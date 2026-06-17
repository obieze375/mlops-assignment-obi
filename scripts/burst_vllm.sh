#!/usr/bin/env bash
# Fire a burst of concurrent chat-completions against vLLM to exercise Grafana panels.
#
# Usage:
#   bash scripts/burst_vllm.sh          # 20 requests (default)
#   bash scripts/burst_vllm.sh 50       # custom count
#
# Requires vLLM listening on localhost:8000 (see scripts/start_vllm.sh).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "${ROOT}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

MODEL="${VLLM_MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
BASE_URL="${VLLM_BASE_URL:-http://localhost:8000/v1}"
N="${1:-20}"
PROMPT="${2:-SELECT 1}"
MAX_TOKENS="${MAX_TOKENS:-32}"

echo "Burst: ${N} concurrent requests -> ${BASE_URL}/chat/completions"
echo "Model: ${MODEL}  max_tokens: ${MAX_TOKENS}"

started=$(date +%s)
for i in $(seq 1 "$N"); do
  curl -s "${BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"${PROMPT}\"}],\"max_tokens\":${MAX_TOKENS}}" \
    -o /dev/null -w "req ${i}: HTTP %{http_code}\n" &
done
wait
elapsed=$(( $(date +%s) - started ))
echo "Done in ${elapsed}s. Check Grafana: http://localhost:3000 (dashboard: vLLM serving)"
