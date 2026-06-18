#!/usr/bin/env bash
# Phase 1 smoke test: readable vLLM health + manual SQL query output.
#
# Usage:
#   bash scripts/vllm_manual_query.sh
#   bash scripts/vllm_manual_query.sh "Write SQL: SELECT 1"
#
# Screenshot the terminal output for screenshots/vllm_manual_query.png

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "${ROOT}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

BASE="${VLLM_BASE_URL:-http://localhost:8000/v1}"
BASE="${BASE%/v1}"
MODEL="${VLLM_MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
QUESTION="${1:-Write SQL: list top 5 schools by enrollment}"
MAX_TOKENS="${MAX_TOKENS:-128}"

bar() { printf '\n%s\n' "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }
section() { bar; printf '  %s\n' "$1"; bar; }

json_pretty() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  else
    uv run python -m json.tool
  fi
}

extract_content() {
  uv run python - <<'PY' "$1"
import json, sys
data = json.loads(sys.argv[1])
print(data["choices"][0]["message"]["content"])
PY
}

section "1) vLLM health"
health_body="$(mktemp)"
health_code="$(curl -sS -o "$health_body" -w '%{http_code}' "${BASE}/health" || true)"
echo "GET ${BASE}/health"
echo "HTTP status: ${health_code}"
if [ -s "$health_body" ]; then
  cat "$health_body" | json_pretty 2>/dev/null || cat "$health_body"
else
  echo "(empty body — OK if status is 200)"
fi
rm -f "$health_body"

section "2) Loaded models"
curl -sS "${BASE}/v1/models" | json_pretty

section "3) Manual chat completion"
echo "Model:   ${MODEL}"
echo "Question: ${QUESTION}"
echo

payload="$(QUESTION="$QUESTION" MODEL="$MODEL" MAX_TOKENS="$MAX_TOKENS" uv run python - <<'PY'
import json, os
print(json.dumps({
    "model": os.environ["MODEL"],
    "messages": [{"role": "user", "content": os.environ["QUESTION"]}],
    "max_tokens": int(os.environ["MAX_TOKENS"]),
}))
PY
)"

response="$(curl -sS "${BASE}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "$payload")"

section "4) Assistant reply (for screenshot)"
extract_content "$response"

section "5) Usage summary"
if command -v jq >/dev/null 2>&1; then
  echo "$response" | jq '{
    model,
    finish_reason: .choices[0].finish_reason,
    usage
  }'
else
  echo "$response" | uv run python -m json.tool | head -30
fi

echo
echo "Done. Screenshot sections 1–4 for screenshots/vllm_manual_query.png"
