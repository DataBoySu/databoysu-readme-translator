#!/usr/bin/env bash
set -euo pipefail

# Clean entrypoint wrapper for DataBoySu Readme Translator
# - Downloads a model into the runner cache if necessary
# - Invokes the packaged translator module

ACTION_NAME="databoysu-readme-translator"
RUNNER_CACHE=${RUNNER_TOOL_CACHE:-"$HOME/.cache"}
MODEL_CACHE_DIR="$RUNNER_CACHE/$ACTION_NAME/models"
mkdir -p "$MODEL_CACHE_DIR"

# Default Aya Expanse 8B (Q4_K_M) model hosted on Hugging Face
DEFAULT_MODEL_URL="https://huggingface.co/lmstudio-community/aya-expanse-8b-GGUF/resolve/main/aya-expanse-8b-Q4_K_M.gguf"

# Inputs passed via env or defaults
INPUT_LANG="${INPUT_LANG:-de}"
INPUT_MODEL_PATH="${INPUT_MODEL_PATH:-}"
INPUT_MODEL_URL="${INPUT_MODEL_URL:-}"
INPUT_NAV_TARGET="${INPUT_NAV_TARGET:-README.md}"

echo "[entrypoint] lang=$INPUT_LANG nav_target=$INPUT_NAV_TARGET"

# Prefer explicit model path, then model URL, then default cached model
MODEL_PATH="$INPUT_MODEL_PATH"
if [ -z "$MODEL_PATH" ] && [ -n "$INPUT_MODEL_URL" ]; then
  FNAME=$(basename "$INPUT_MODEL_URL")
  MODEL_PATH="$MODEL_CACHE_DIR/$FNAME"
  if [ ! -f "$MODEL_PATH" ]; then
    echo "[entrypoint] downloading model from $INPUT_MODEL_URL -> $MODEL_PATH"
    curl -sSL "$INPUT_MODEL_URL" -o "$MODEL_PATH"
  else
    echo "[entrypoint] using cached model $MODEL_PATH"
  fi
fi

if [ -z "$MODEL_PATH" ]; then
  # attempt to use a default cached model filename
  FNAME=$(basename "$DEFAULT_MODEL_URL")
  MODEL_PATH="$MODEL_CACHE_DIR/$FNAME"
  if [ ! -f "$MODEL_PATH" ]; then
    echo "[entrypoint] cache miss; downloading default Aya model -> $MODEL_PATH"
    curl -sSL "$DEFAULT_MODEL_URL" -o "$MODEL_PATH"
  else
    echo "[entrypoint] using cached default model $MODEL_PATH"
  fi
else
  echo "[entrypoint] model_path=$MODEL_PATH"
fi

# Run translator as a module (import-safe)
PY_CMD=(python -m readme_translator_action.translator.translate --lang "$INPUT_LANG" --nav-target "$INPUT_NAV_TARGET")
if [ -n "$MODEL_PATH" ]; then
  PY_CMD+=(--model-path "$MODEL_PATH")
fi

echo "[entrypoint] running: ${PY_CMD[*]}"
"${PY_CMD[@]}"
