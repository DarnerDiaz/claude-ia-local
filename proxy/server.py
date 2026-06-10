#!/usr/bin/env python3
"""
MLX Native Anthropic Server — Claude Code on Apple Silicon.

Entry point. The implementation is split across the `mlx_server` package
(sitting next to this file); this script just wires it together and serves.
It converts Anthropic tool format <-> the model's native function calling
format (Gemma 4's `<|tool_call>call:Name{...}<tool_call|>`, Llama 3.3's raw-JSON
`{"type":"function",...}`, and the common HuggingFace `<tool_call>` JSON form
used by Qwen and others).

Pick a model from the lineup with the MLX_MODEL env var:
    MLX_MODEL=divinetribe/gemma-4-31b-it-abliterated-4bit-mlx            (THE QUICK ONE — default, our own MLX upload)
    MLX_MODEL=divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx    (THE WISE ONE — our own MLX upload)
    MLX_MODEL=mlx-community/Qwen3.5-122B-A10B-4bit                       (THE BEAST)

NOTE FOR CONTRIBUTORS: this file is the source of truth. `setup.sh` installs it
at `~/.local/mlx-native-server/server.py` via a symlink, so edits here take
effect on the running server after a restart — no re-copying needed. Because it
is invoked through that symlink, we resolve the *real* path below and add its
directory to sys.path so the sibling `mlx_server` package is importable.
"""

import os
import sys

# Make the sibling `mlx_server` package importable even when this file is run
# through the install symlink (~/.local/mlx-native-server/server.py). realpath
# resolves the symlink back to the repo's proxy/ directory.
_REAL_DIR = os.path.dirname(os.path.realpath(__file__))
if _REAL_DIR not in sys.path:
    sys.path.insert(0, _REAL_DIR)

from mlx_server import config, model_loader, metrics
from mlx_server.http_app import make_server


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  MLX Native Anthropic Server                    ║")
    print("║  Claude Code → MLX → Apple Silicon (direct)     ║")
    print("║  Tool use: enabled (Anthropic ↔ Llama native)   ║")
    print("║  Prompt caching: enabled (KV reuse)             ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    model_loader.load_model()
    metrics.mark_start(config.MODEL_PATH)

    print()
    print(f"Serving Anthropic Messages API on http://localhost:{config.PORT}")
    print(f"Model: {config.MODEL_PATH}")
    print(f"KV cache: {config.KV_BITS}-bit quantization (start at token {config.KV_QUANT_START})" if config.KV_BITS else "KV cache: full precision")
    print(f"Prompt cache: enabled (KV reuse across requests)")
    print(f"Tool retry: up to {config.MAX_TOOL_RETRIES} retries on garbled tool calls")
    print()
    print(f"Dashboard:  http://localhost:{config.PORT}/dashboard")
    print()
    print("Claude Code config:")
    print(f"  ANTHROPIC_BASE_URL=http://localhost:{config.PORT}")
    print(f"  ANTHROPIC_API_KEY=sk-local")
    print()

    server = make_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
