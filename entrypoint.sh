#!/usr/bin/env bash
set -euo pipefail

# Entrypoint wrapper for DataBoySu Readme Translator
# - Handles optional model download to runner cache
# - Invokes the Python translator CLI

ACTION_NAME="databoysu-readme-translator"
RUNNER_CACHE=${RUNNER_TOOL_CACHE:-"$HOME/.cache"}
MODEL_CACHE_DIR="$RUNNER_CACHE/$ACTION_NAME/models"
mkdir -p "$MODEL_CACHE_DIR"

# Inputs passed via env or defaults
INPUT_LANG="${INPUT_LANG:-${INPUT_LANG:-de}}"
INPUT_MODEL_PATH="${INPUT_MODEL_PATH:-}"
INPUT_MODEL_URL="${INPUT_MODEL_URL:-}"
INPUT_NAV_TARGET="${INPUT_NAV_TARGET:-README.md}"
INPUT_DRY_RUN="${INPUT_DRY_RUN:-false}"

echo "[entrypoint] lang=$INPUT_LANG nav_target=$INPUT_NAV_TARGET dry_run=$INPUT_DRY_RUN"

MODEL_PATH="$INPUT_MODEL_PATH"
if [ -z "$MODEL_PATH" ] && [ -n "$INPUT_MODEL_URL" ]; then
  # download into model cache with a deterministic filename
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
  echo "[entrypoint] no model path provided; translator will use bundled default if available"
else
  echo "[entrypoint] model_path=$MODEL_PATH"
fi

PY_CMD=(python readme-translator-action/translator/translate.py --lang "$INPUT_LANG" --nav-target "$INPUT_NAV_TARGET")
if [ -n "$MODEL_PATH" ]; then
  PY_CMD+=(--model-path "$MODEL_PATH")
fi
if [ "$INPUT_DRY_RUN" = "true" ] || [ "$INPUT_DRY_RUN" = "True" ]; then
  PY_CMD+=(--dry-run)
fi

echo "[entrypoint] running: ${PY_CMD[*]}"
"${PY_CMD[@]}"
