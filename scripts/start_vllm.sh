#!/usr/bin/env bash
#
# Start vLLM with tuned configuration for Qwen3-30B-A3B on 1× H100 80GB.
# Workload: ~1.5-3K token prompts, short structured SQL/JSON outputs,
# ~2-3 dependent LLM calls per agent request.

set -euo pipefail

if ! compgen -G "/usr/include/python3.*/Python.h" > /dev/null; then
  echo "ERROR: Python.h not found. vLLM torch.compile needs python3-dev:"
  echo "  sudo apt-get update && sudo apt-get install -y python3-dev build-essential"
  exit 1
fi

MODEL="${VLLM_MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"

# Load HF_TOKEN from .env if present (repo root)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "${ROOT}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

exec uv run python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.92 \
    --max-num-seqs 64 \
    --max-num-batched-tokens 8192 \
    --enable-prefix-caching
