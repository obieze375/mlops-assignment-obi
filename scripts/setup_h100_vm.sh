#!/usr/bin/env bash
# Post-provision setup for the Nebius H100 assignment VM.
# Run as ubuntu after SSH'ing into the terraform-provisioned instance.

set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"

echo "==> Installing system deps"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  docker.io docker-compose-v2 python3-dev build-essential jq curl git

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker "$USER" || true

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

echo "==> Python deps"
uv sync

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Fill HF_TOKEN and Langfuse keys in .env before running evals."
fi

echo "==> BIRD data"
uv run python scripts/load_data.py

echo "==> Observability stack"
sudo docker compose up -d

echo "==> Waiting for Grafana/Prometheus/Langfuse"
for port in 9090 3000 3001; do
  for i in $(seq 1 30); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/" || true)
    if [ "$code" != "000" ]; then break; fi
    sleep 5
  done
  echo "port ${port}: ${code:-unknown}"
done

echo "==> Start vLLM (background)"
nohup bash scripts/start_vllm.sh > /tmp/vllm.log 2>&1 &
echo "vLLM log: /tmp/vllm.log"

echo "==> Wait for vLLM /health"
for i in $(seq 1 120); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "vLLM ready"
    break
  fi
  sleep 10
done

echo "==> Start agent server (background)"
nohup uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001 > /tmp/agent.log 2>&1 &
sleep 3
curl -sf http://localhost:8001/health && echo "agent ready"

cat <<'EOF'

Next steps (manual):
1. Add Langfuse keys to .env (Phase 4) and restart agent.
2. Run baseline eval: uv run python evals/run_eval.py
3. Run load test: uv run python load_test/driver.py --rps 10 --duration 300
4. Capture screenshots into screenshots/

EOF
