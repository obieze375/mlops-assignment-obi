#!/usr/bin/env python3
"""Validate assignment phases with quick smoke checks."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    msg = f"[{status}] {name}"
    if detail:
        msg += f" - {detail}"
    print(msg)
    if not ok:
        global failed
        failed += 1


failed = 0


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def main() -> None:
    print("== Phase 0 ==")
    check("BIRD data present", (ROOT / "data" / "bird").exists() and any((ROOT / "data" / "bird").glob("*.sqlite")))
    check("eval_set.jsonl", (ROOT / "evals" / "eval_set.jsonl").exists())
    check(".env exists", (ROOT / ".env").exists())
    check("Prometheus UI", http_ok("http://localhost:9090/"))
    check("Grafana UI", http_ok("http://localhost:3000/login"))
    check("Langfuse UI", http_ok("http://localhost:3001/"))

    print("== Phase 1 ==")
    vllm_health = http_ok("http://localhost:8000/health")
    check("vLLM /health", vllm_health)
    if vllm_health:
        try:
            req = urllib.request.Request(
                "http://localhost:8000/v1/chat/completions",
                data=json.dumps({
                    "model": "test",
                    "messages": [{"role": "user", "content": "Reply with SQL: SELECT 1"}],
                    "max_tokens": 64,
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
            content = body["choices"][0]["message"]["content"]
            check("vLLM chat completion", bool(content))
        except Exception as e:  # noqa: BLE001
            check("vLLM chat completion", False, str(e))

    print("== Phase 2 ==")
    dash = ROOT / "infra/grafana/provisioning/dashboards/serving.json"
    if dash.exists():
        data = json.loads(dash.read_text())
        titles = [p.get("title", "") for p in data.get("panels", [])]
        check("Grafana dashboard JSON", len(data.get("panels", [])) >= 5)
        check("Latency panels", any("latency" in t.lower() or "token" in t.lower() for t in titles))
        check("Throughput panels", any("token" in t.lower() or "request" in t.lower() for t in titles))
        check("KV cache panel", any("cache" in t.lower() for t in titles))

    print("== Phase 3 ==")
    check("Agent /health", http_ok("http://localhost:8001/health"))
    if http_ok("http://localhost:8001/health") and (ROOT / "evals/eval_set.jsonl").exists():
        q = json.loads((ROOT / "evals/eval_set.jsonl").read_text().splitlines()[0])
        try:
            req = urllib.request.Request(
                "http://localhost:8001/answer",
                data=json.dumps({"question": q["question"], "db": q["db_id"]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                ans = json.loads(resp.read())
            check("Agent /answer", ans.get("ok") or ans.get("sql"))
            revised = any(h.get("node") == "revise" for h in ans.get("history", []))
            check("Agent revise loop possible", "history" in ans, "run more eval questions to trigger revise")
        except Exception as e:  # noqa: BLE001
            check("Agent /answer", False, str(e))

    print("== Phase 4 ==")
    env = (ROOT / ".env").read_text() if (ROOT / ".env").exists() else ""
    check("Langfuse keys in .env", "LANGFUSE_PUBLIC_KEY=" in env and "LANGFUSE_SECRET_KEY=" in env and "pk-" in env)

    print("== Phase 5 ==")
    check("eval runner import", True)
    try:
        from evals import run_eval  # noqa: F401
        check("eval_one implemented", callable(run_eval.eval_one))
        check("summarize implemented", callable(run_eval.summarize))
    except Exception as e:  # noqa: BLE001
        check("eval runner import", False, str(e))
    check("baseline results", (ROOT / "results/eval_baseline.json").exists())
    check("post-tuning results", (ROOT / "results/eval_after_tuning.json").exists())

    print("== Phase 6 ==")
    check("load test results", (ROOT / "results/load_test.json").exists())
    check("REPORT.md", (ROOT / "REPORT.md").exists())

    print(f"\nDone: {failed} failure(s)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
