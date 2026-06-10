#!/bin/bash
# MLX Native Anthropic Server — start helper
# Speaks the Anthropic Messages API directly. No proxy. No translation layer.
#
# Usage:
#   bash scripts/iniciar-servidor-mlx.sh                              # default Gemma 4 31B
#   MLX_MODEL=mlx-community/Qwen3.5-122B-A10B-4bit bash scripts/iniciar-servidor-mlx.sh
#   MODELO_MLX=mlx-community/Qwen3.5-122B-A10B-4bit bash scripts/iniciar-servidor-mlx.sh  # alias
#   bash scripts/iniciar-servidor-mlx.sh mlx-community/Llama-3.3-70B-Instruct-abliterated-8bit

# Precedencia: arg posicional > MLX_MODEL > MODELO_MLX (alias) > default.
MODEL="${1:-${MLX_MODEL:-${MODELO_MLX:-divinetribe/gemma-4-31b-it-abliterated-4bit-mlx}}}"
PORT="${MLX_PORT:-${PUERTO_MLX:-4000}}"
PYTHON="${MLX_PYTHON:-$HOME/.local/mlx-server/bin/python3}"
SERVER="${MLX_SERVER:-$HOME/.local/mlx-native-server/server.py}"

echo "Starting MLX Native Anthropic Server"
echo "  model: $MODEL"
echo "  port:  $PORT"

MLX_MODEL="$MODEL" MLX_PORT="$PORT" exec "$PYTHON" "$SERVER"
