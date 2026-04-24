#!/bin/bash
# Persistent model download — auto-restarts on every failure.
# Useful for big models (Qwen 122B is ~75 GB) on flaky connections.
#
# Usage:
#   bash scripts/persistent-download.sh                              # default Gemma 4 31B
#   bash scripts/persistent-download.sh qwen                         # Qwen 3.5 122B
#   bash scripts/persistent-download.sh llama                        # Llama 3.3 70B
#   MLX_MODEL=<hf-id> bash scripts/persistent-download.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Persistent MLX model download ==="
echo "Will keep retrying until the model is fully cached."
echo ""

while true; do
  echo "[$(date)] Starting download attempt..."
  if bash "$SCRIPT_DIR/download-and-import.sh" "$@"; then
    echo ""
    echo "=== DONE! Model is ready ==="
    break
  fi
  echo "[$(date)] Download dropped. Restarting in 10s..."
  sleep 10
done
