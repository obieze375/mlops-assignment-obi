#!/usr/bin/env bash
# CPU stand-in for local development when no H100 is attached.
# Use scripts/start_vllm.sh on the Nebius H100 VM for the real assignment model.

set -euo pipefail

MODEL="${VLLM_MODEL:-Qwen/Qwen3-0.6B}"

exec uv run python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --device cpu \
    --dtype float32 \
    --max-model-len 4096 \
    --disable-log-requests
