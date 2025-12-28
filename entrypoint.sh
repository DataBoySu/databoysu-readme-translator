#!/bin/bash
set -e

# Arguments passed from action.yml
TARGET_LANG="$1"
NAV_TARGET="$2"
MODEL_URL="$3"
MODE="$4"

# Resolve the directory where this script (and the action) resides
ACTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[INFO] Action Directory: $ACTION_DIR"
echo "[INFO] Target Language: $TARGET_LANG"
echo "[INFO] Mode: ${MODE:-translate}"

if [ "$MODE" != "navbar" ]; then
    # 1. Install Python Dependencies
    echo "[INFO] Installing dependencies..."
    pip install -r "$ACTION_DIR/requirements.txt"

    # 2. Model Management
    # Use the cached directory provided by action.yml, or fallback to local models dir
    if [ -n "$MODEL_CACHE_DIR" ]; then
        MODEL_DIR="$MODEL_CACHE_DIR"
    else
        MODEL_DIR="$ACTION_DIR/models"
    fi

    MODEL_FILE="$MODEL_DIR/model.gguf"

    if [ ! -f "$MODEL_FILE" ]; then
        echo "[INFO] Model not found. Downloading from $MODEL_URL..."
        mkdir -p "$MODEL_DIR"
        # Use curl with fail (-f), location (-L), and show error (-S)
        curl -fL -S "$MODEL_URL" -o "$MODEL_FILE"
    else
        echo "[INFO] Model found at $MODEL_FILE"
    fi
fi

# 3. Run Translation
echo "[INFO] Starting Translation Script..."
python "$ACTION_DIR/translator/translate.py" \
  --lang "$TARGET_LANG" \
  --nav-target "$NAV_TARGET" \
  --model-path "${MODEL_FILE:-}" \
  --mode "${MODE:-translate}"

echo "[SUCCESS] Entrypoint finished."