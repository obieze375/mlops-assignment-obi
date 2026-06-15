"""Minimal OpenAI-compatible mock for local agent/o11y testing without a GPU.

Usage:
    uv run python scripts/mock_vllm_server.py
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: ANN002
        return

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/v1/models"}:
            self._json(200, {"status": "ok"} if self.path == "/health" else {"data": []})
        elif self.path == "/metrics":
            metrics = "\n".join([
                "# HELP vllm:num_requests_running Active requests",
                "# TYPE vllm:num_requests_running gauge",
                "vllm:num_requests_running 1",
                "# HELP vllm:num_requests_waiting Waiting requests",
                "# TYPE vllm:num_requests_waiting gauge",
                "vllm:num_requests_waiting 0",
                "# HELP vllm:generation_tokens_total Generated tokens",
                "# TYPE vllm:generation_tokens_total counter",
                "vllm:generation_tokens_total 1200",
                "# HELP vllm:prompt_tokens_total Prompt tokens",
                "# TYPE vllm:prompt_tokens_total counter",
                "vllm:prompt_tokens_total 8000",
                "# HELP vllm:gpu_cache_usage_perc GPU KV cache usage",
                "# TYPE vllm:gpu_cache_usage_perc gauge",
                "vllm:gpu_cache_usage_perc 0.35",
                "# HELP vllm:e2e_request_latency_seconds E2E latency",
                "# TYPE vllm:e2e_request_latency_seconds histogram",
                'vllm:e2e_request_latency_seconds_bucket{le="0.5"} 4',
                'vllm:e2e_request_latency_seconds_bucket{le="1.0"} 9',
                'vllm:e2e_request_latency_seconds_bucket{le="2.0"} 10',
                'vllm:e2e_request_latency_seconds_bucket{le="+Inf"} 10',
                "vllm:e2e_request_latency_seconds_sum 6.5",
                "vllm:e2e_request_latency_seconds_count 10",
                "# HELP vllm:time_to_first_token_seconds TTFT",
                "# TYPE vllm:time_to_first_token_seconds histogram",
                'vllm:time_to_first_token_seconds_bucket{le="0.1"} 6',
                'vllm:time_to_first_token_seconds_bucket{le="0.5"} 10',
                'vllm:time_to_first_token_seconds_bucket{le="+Inf"} 10',
                "vllm:time_to_first_token_seconds_sum 2.1",
                "vllm:time_to_first_token_seconds_count 10",
                "# HELP vllm:request_success_total Successful requests",
                "# TYPE vllm:request_success_total counter",
                "vllm:request_success_total 10",
                "# HELP vllm:request_failure_total Failed requests",
                "# TYPE vllm:request_failure_total counter",
                "vllm:request_failure_total 0",
                "",
            ])
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(metrics.encode())
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        messages = payload.get("messages", [])
        text = "\n".join(m.get("content", "") for m in messages if isinstance(m, dict))

        if "JSON" in text or "json" in text.lower():
            if "0 rows" in text or "ERROR" in text:
                content = '{"ok": false, "issue": "zero rows for a question that expects data"}'
            else:
                content = '{"ok": true, "issue": ""}'
        elif "corrected" in text.lower() or "revise" in text.lower() or "Verifier issue" in text:
            content = "```sql\nSELECT name FROM school WHERE county = 'Alameda' LIMIT 5\n```"
        elif "school" in text.lower() and "alameda" in text.lower():
            content = "```sql\nSELECT bad_column FROM school WHERE county = 'Alameda'\n```"
        else:
            m = re.search(r"Question:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
            q = (m.group(1).strip() if m else text)[:120]
            content = f"```sql\nSELECT 1 AS answer -- mock for: {q}\n```"

        self._json(200, {
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 40},
        })


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("mock vLLM on http://0.0.0.0:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
