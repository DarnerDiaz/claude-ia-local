"""MLX model loading.

Loads the model + tokenizer once at startup and holds them as module globals
(`model`, `tokenizer`) that the generation pipeline reads via the module
reference. Imports MLX, so it is NOT safe to import in pure unit tests.
"""

import time

import mlx.core as mx
from mlx_lm.utils import load

from . import config
from .config import log

# ─── Globals (populated by load_model) ───────────────────────────────────────

model = None
tokenizer = None


GEMMA4_CHAT_TEMPLATE = (
    "{{ bos_token }}"
    "{% set ns = namespace(system='') %}"
    "{% for message in messages %}{% if message['role'] == 'system' %}{% set ns.system = message['content'] %}{% endif %}{% endfor %}"
    "{% for message in messages %}"
    "{% if message['role'] == 'user' %}"
    "<|turn>user\n{% if ns.system and loop.first %}{{ ns.system }}\n\n{% endif %}{{ message['content'] }}<turn|>"
    "{% elif message['role'] == 'assistant' %}"
    "<|turn>model\n{{ message['content'] }}<turn|>"
    "{% elif message['role'] == 'tool' %}"
    "<|turn>tool_response\n{{ message['content'] }}<turn|>"
    "{% endif %}"
    "{% endfor %}"
    "{% if add_generation_prompt %}<|turn>model\n{% endif %}"
)

def load_model():
    global model, tokenizer
    log(f"Loading model: {config.MODEL_PATH}")
    t0 = time.time()
    model, tokenizer = load(config.MODEL_PATH)
    mx.eval(model.parameters())
    # Fallback chat template if model doesn't provide one (Llama 3.3 has its own)
    if not getattr(tokenizer, 'chat_template', None):
        tokenizer.chat_template = GEMMA4_CHAT_TEMPLATE
        log("Injected Gemma 4 chat template")
    elapsed = time.time() - t0
    log(f"Model loaded in {elapsed:.1f}s")

    # Safety net: Gemma uses sliding-window attention → RotatingKVCache, which
    # mlx-lm can't quantize yet ("RotatingKVCache Quantization NYI"). The
    # default for MLX_KV_BITS is already 0, but if a user explicitly sets it to
    # 8 and happens to be running Gemma, auto-disable it so inference doesn't
    # 500 on the first call. (Credit: asdmoment, PR #7.)
    if config.KV_BITS and "gemma" in config.MODEL_PATH.lower():
        log("Gemma detected: disabling KV cache quantization (RotatingKVCache NYI)")
        config.KV_BITS = 0

    log(f"KV cache quantization: {config.KV_BITS}-bit" if config.KV_BITS else "KV cache: full precision")
