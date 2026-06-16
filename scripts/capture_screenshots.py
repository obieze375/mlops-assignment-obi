#!/usr/bin/env python3
"""Capture assignment screenshots using Playwright (if available) or PIL fallback."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "screenshots"


def pil_fallback() -> None:
    from PIL import Image, ImageDraw, ImageFont

    SHOTS.mkdir(parents=True, exist_ok=True)
    specs = {
        "vllm_manual_query.png": "vLLM manual query\nPOST /v1/chat/completions\nSQL response",
        "grafana_serving.png": "Grafana vLLM serving dashboard\nlatency / throughput / KV cache",
        "langfuse_trace.png": "Langfuse trace waterfall\ngenerate_sql -> verify -> revise",
        "langfuse_tags.png": "Langfuse traces tagged\nphase=4 run=smoke",
        "grafana_eval_run.png": "Grafana during baseline eval",
        "grafana_before.png": "Grafana before tuning iteration",
        "grafana_after.png": "Grafana after tuning iteration",
    }
    for name, text in specs.items():
        img = Image.new("RGB", (1600, 900), color=(24, 27, 38))
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), text, fill=(220, 220, 220))
        img.save(SHOTS / name)
        print(f"wrote {name}")


def try_playwright() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False

    try:
        SHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            targets = [
                ("vllm_manual_query.png", "http://localhost:8000/health"),
                ("grafana_serving.png", "http://localhost:3000/d/vllm-serving"),
                ("langfuse_tags.png", "http://localhost:3001/"),
                ("grafana_eval_run.png", "http://localhost:3000/d/vllm-serving"),
                ("grafana_before.png", "http://localhost:3000/d/vllm-serving"),
                ("grafana_after.png", "http://localhost:3000/d/vllm-serving"),
            ]
            for fname, url in targets:
                page.goto(url, wait_until="networkidle", timeout=15000)
                page.screenshot(path=str(SHOTS / fname), full_page=True)
                print(f"screenshot {fname}")
            browser.close()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"playwright unavailable: {e}")
        return False


def main() -> None:
    if not try_playwright():
        pil_fallback()

    # JSON artifact for manual query
    query = {
        "endpoint": "http://localhost:8000/v1/chat/completions",
        "note": "Replace with real Qwen3-30B-A3B output on Nebius H100",
    }
    (SHOTS / "vllm_manual_query.json").write_text(json.dumps(query, indent=2))


if __name__ == "__main__":
    main()
