"""Configuration + logging.

All tunables come from environment variables so launchers and scripts can
override them at startup. Importing this module has no side effects beyond
reading os.environ — it pulls in no MLX dependency, so pure modules and tests
can import it freely.
"""

import os
import sys
import time

# ─── Configuration ───────────────────────────────────────────────────────────

MODEL_PATH = os.environ.get("MLX_MODEL", "divinetribe/gemma-4-31b-it-abliterated-4bit-mlx")
PORT = int(os.environ.get("MLX_PORT", "4000"))
KV_BITS = int(os.environ.get("MLX_KV_BITS", "0"))  # Gemma 4 RotatingKVCache doesn't support quantization
PREFILL_SIZE = int(os.environ.get("MLX_PREFILL_SIZE", "8192"))
DEFAULT_MAX_TOKENS = int(os.environ.get("MLX_MAX_TOKENS", "8192"))
KV_QUANT_START = int(os.environ.get("MLX_KV_QUANT_START", "256"))
MAX_TOOL_RETRIES = int(os.environ.get("MLX_TOOL_RETRIES", "2"))
# Browser mode: strip Claude Code bloat, keep only MCP tools
BROWSER_MODE = os.environ.get("MLX_BROWSER_MODE", "0") == "1"
# Code mode: auto-detect Claude Code coding sessions and replace the huge harness
# system prompt with a Llama-tuned one. Set MLX_CODE_MODE=0 to disable.
CODE_MODE_ENABLED = os.environ.get("MLX_CODE_MODE", "1") != "0"


# ─── Logging ─────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)
