#!/bin/bash
# Upload an MLX-quantized model folder to your HuggingFace account.
# Uses hf_transfer for parallel chunked uploads (50-200 MB/s vs 1-2 MB/s
# for the plain Python path).
#
# Usage:
#   bash scripts/upload-mlx-quant.sh <local-folder> <hf-repo-id>
#
# Examples:
#   bash scripts/upload-mlx-quant.sh \
#     ~/.cache/huggingface/hub/gemma-4-31b-it-abliterated-4bit-mlx \
#     divinetribe/gemma-4-31b-it-abliterated-4bit-mlx
#
#   bash scripts/upload-mlx-quant.sh ./my-quant divinetribe/my-quant
#
# Requirements:
#   - You must be logged in:  hf auth login   (or have HF_TOKEN exported)
#   - hf_transfer installed in the MLX venv (the script will install it for you)

set -e

LOCAL_DIR="${1:-}"
REPO_ID="${2:-}"

if [ -z "$LOCAL_DIR" ] || [ -z "$REPO_ID" ]; then
  echo "usage: bash scripts/upload-mlx-quant.sh <local-folder> <hf-repo-id>"
  echo "example: bash scripts/upload-mlx-quant.sh ~/my-quant divinetribe/my-quant"
  exit 1
fi

if [ ! -d "$LOCAL_DIR" ]; then
  echo "ERROR: $LOCAL_DIR is not a directory"
  exit 1
fi

if [ ! -f "$LOCAL_DIR/config.json" ]; then
  echo "ERROR: $LOCAL_DIR has no config.json — doesn't look like a model folder"
  exit 1
fi

MLX_PYTHON="${MLX_PYTHON:-$HOME/.local/mlx-server/bin/python3}"
MLX_PIP="${MLX_PIP:-$HOME/.local/mlx-server/bin/pip}"

if [ ! -x "$MLX_PYTHON" ]; then
  echo "ERROR: MLX virtualenv not found at $MLX_PYTHON — run setup.sh first"
  exit 1
fi

# Make sure hf_transfer is installed (one-time)
if ! "$MLX_PYTHON" -c "import hf_transfer" 2>/dev/null; then
  echo "Installing hf_transfer for fast parallel uploads..."
  "$MLX_PIP" install --quiet hf_transfer
fi

# Auto-generate a model card if none exists (or only has frontmatter)
README="$LOCAL_DIR/README.md"
README_LINES=$(wc -l < "$README" 2>/dev/null || echo 0)
if [ ! -f "$README" ] || [ "$README_LINES" -lt 25 ]; then
  echo "Generating model card from config.json..."
  "$MLX_PYTHON" - <<PY
import json, os, re
local = "$LOCAL_DIR"
repo  = "$REPO_ID"
cfg   = json.load(open(os.path.join(local, "config.json")))
quant = cfg.get("quantization", {}) or cfg.get("quantization_config", {}) or {}
bits  = quant.get("bits", "?")
group = quant.get("group_size", "?")
arch  = (cfg.get("architectures") or ["unknown"])[0]
mtype = cfg.get("model_type", "unknown")
name  = repo.split("/")[-1]
size_bytes = sum(
    os.path.getsize(os.path.join(local, f))
    for f in os.listdir(local)
    if f.endswith(".safetensors")
)
size_gb = size_bytes / 1024**3

card = f"""---
license: apache-2.0
tags:
- mlx
- mlx-{bits}bit
- quantized
- {mtype}
language:
- en
library_name: mlx
pipeline_tag: text-generation
---

# {name}

A {bits}-bit MLX quantization for fast on-device inference on Apple Silicon.

- **Architecture:** `{arch}` ({mtype})
- **Quantization:** {bits}-bit affine, group size {group}
- **Format:** MLX safetensors
- **Footprint:** ~{size_gb:.1f} GB on disk

## Usage

\`\`\`python
from mlx_lm import load, generate
model, tokenizer = load("{repo}")
print(generate(model, tokenizer, prompt="Hello", max_tokens=200))
\`\`\`

Or via the launcher / setup script in [nicedreamzapp/claude-code-local](https://github.com/nicedreamzapp/claude-code-local):

\`\`\`bash
MLX_MODEL={repo} bash scripts/start-mlx-server.sh
\`\`\`
"""

with open(os.path.join(local, "README.md"), "w") as fh:
    fh.write(card)
print(f"  wrote {os.path.join(local, 'README.md')}")
PY
fi

echo ""
echo "=== Uploading $LOCAL_DIR -> $REPO_ID ==="
echo "    fast path: hf_transfer ENABLED"
echo ""

HF_HUB_ENABLE_HF_TRANSFER=1 "$MLX_PYTHON" - <<PY
import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import HfApi, create_repo

api = HfApi()
me = api.whoami()
print(f"Logged in as {me['name']}")

create_repo("$REPO_ID", repo_type="model", exist_ok=True, private=False)
print(f"Repo $REPO_ID ready.")

api.upload_folder(
    folder_path="$LOCAL_DIR",
    repo_id="$REPO_ID",
    repo_type="model",
    commit_message="Upload MLX quant",
)
print("UPLOAD COMPLETE")
print(f"https://huggingface.co/$REPO_ID")
PY

echo ""
echo "=== Done. Add it to your lineup with:"
echo "    MLX_MODEL=$REPO_ID bash scripts/start-mlx-server.sh"
