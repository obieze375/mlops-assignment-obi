# MLOps Assignment Report

## 1. Serving configuration (Phase 1)

Target model: `Qwen/Qwen3-30B-A3B-Instruct-2507` on 1× H100 80GB (`gpu-h100-sxm` / `1gpu-16vcpu-200gb`).

| Flag | Value | Rationale |
|------|-------|-----------|
| `--dtype auto` | auto | Lets vLLM pick the best weight format supported on H100. |
| `--max-model-len 8192` | 8192 | Covers ~1.5–3K-token schemas + short SQL/JSON outputs with headroom. |
| `--gpu-memory-utilization 0.92` | 0.92 | Uses most of H100 memory for KV cache while leaving slack for CUDA graphs. |
| `--max-num-seqs 64` | 64 | Raises concurrent agent requests; MoE 3B-active keeps per-seq memory moderate. |
| `--max-num-batched-tokens 8192` | 8192 | Improves prefill batching under load without huge latency spikes. |
| `--enable-prefix-caching` | on | Reuses repeated schema prefixes across agent calls. |
| `--disable-log-requests` | on | Removes per-request logging overhead at 10+ RPS. |

Launch: `bash scripts/start_vllm.sh` on the Nebius H100 VM.

**Local validation note:** The cloud agent sandbox has no GPU. A mock OpenAI-compatible server (`scripts/mock_vllm_server.py`) was used to validate agent/eval plumbing. Final numbers below must be re-run on the H100 VM via `scripts/setup_h100_vm.sh`.

## 2. Baseline eval results (Phase 5)

From `results/eval_baseline.json` (mock backend in sandbox):

- Overall pass rate: **0%** (expected with mock LLM)
- Per-iteration pass rate: iter 0/1/2 all **0%**
- Agent loop executed revise paths on targeted questions (see agent history)

Re-run on H100:

```bash
uv run python evals/run_eval.py --out results/eval_baseline.json
```

## 3. SLO tuning (Phase 6)

Target SLO: **P95 end-to-end agent latency < 5s, 10+ RPS for 5 minutes**.

Short mock load test (`results/load_test.json`, 5 RPS × 30s):

- P95 latency: **0.024s** (mock; not representative)
- Achieved RPS: **~5.0**

Planned iteration log on H100 (template):

1. *saw waiting queue grow at 8 RPS → hypothesized `max-num-seqs` too low → raised to 64 → waiting dropped, P95 improved*
2. *saw KV cache > 0.9 → hypothesized concurrency limit → lowered `gpu-memory-utilization` tuning / batch tokens → cache headroom restored*
3. *saw TTFT climb while gen tokens/s flat → hypothesized prefill bottleneck → enabled prefix caching (already on) + tuned `max-num-batched-tokens`*

Re-run on H100:

```bash
uv run python load_test/driver.py --rps 10 --duration 300
uv run python evals/run_eval.py --out results/eval_after_tuning.json
```

## 4. Agent value

The verify→revise loop is wired with `MAX_ITERATIONS = 3`. On a targeted Alameda-schools question the agent produced:

- `generate_sql` → execution error
- `verify` flagged issue → `revise` → re-execute (up to cap)

Per-iteration eval aggregation is implemented in `evals/run_eval.py::summarize()` with carry-forward for early termination. On the real 30B endpoint, compare iter-0 vs iter-2 pass rates to quantify loop value.

## 5. What I'd do with more time

- Add canary eval questions to CI and block deploys on >2pt pass-rate regressions.
- Export vLLM + agent metrics into one RED dashboard with SLO burn-rate panels.
- Cache rendered schemas per `db_id` in Redis to shave repeated prefill tokens.
- Autoscale vLLM max concurrency from KV-cache utilization (closed-loop controller).

## Infrastructure

Terraform manifests: `terraform/` (single H100 VM, Ubuntu 24.04 + CUDA 13 image).

Provision:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill project_id, subnet_id, ssh key
terraform init && terraform apply
ssh ubuntu@$(terraform output -raw public_ip)
bash scripts/setup_h100_vm.sh
```

**Blocker in this sandbox:** Nebius credentials were not available (`nebius profile create` not configured), so the H100 VM was not provisioned from here. Provide Nebius project/subnet IDs and service-account keys to run `terraform apply`.
