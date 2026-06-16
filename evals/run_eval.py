"""Eval runner using execution accuracy.

Reads evals/eval_set.jsonl, calls the agent at AGENT_URL on each question,
then compares the agent's SQL output to the gold SQL by *executed rows*
(canonicalized: sorted, stringified, None-coerced to empty).

Helpers (run_sql / canonicalize / matches) are provided. You implement
eval_one() and summarize().

Run:
    uv run python evals/run_eval.py --out results/eval_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_FILE = ROOT / "evals" / "eval_set.jsonl"
DEFAULT_OUT_FILE = ROOT / "results" / "eval_baseline.json"
DB_DIR = ROOT / "data" / "bird"
AGENT_URL_DEFAULT = "http://localhost:8001/answer"


# ---------- Helpers (provided) -----------------------------------------

def run_sql(db_id: str, sql: str, timeout: float = 5.0) -> tuple[bool, list[tuple] | None, str | None]:
    """Run sql against db_id in read-only mode. Returns (ok, rows, error)."""
    path = DB_DIR / f"{db_id}.sqlite"
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout) as conn:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            return True, rows, None
    except Exception as e:  # noqa: BLE001
        return False, None, f"{type(e).__name__}: {e}"


def canonicalize(rows: list[tuple] | None) -> list[tuple] | None:
    """Sort rows; coerce cells to str; None -> ''."""
    if rows is None:
        return None
    return sorted(tuple("" if c is None else str(c) for c in row) for row in rows)


def matches(gold_rows: list[tuple] | None, pred_rows: list[tuple] | None) -> bool:
    if gold_rows is None or pred_rows is None:
        return False
    return canonicalize(gold_rows) == canonicalize(pred_rows)


# ---------- Implement these (Phase 5) ----------------------------------

def eval_one(question: dict, agent_url: str) -> dict:
    """Score one question. Return a dict capturing per-iteration correctness."""
    db_id = question["db_id"]
    gold_sql = question["gold_sql"]

    ok_gold, gold_rows, gold_err = run_sql(db_id, gold_sql)
    if not ok_gold:
        return {
            "question": question["question"],
            "db_id": db_id,
            "gold_sql": gold_sql,
            "error": f"gold SQL failed: {gold_err}",
            "agent_sql": None,
            "iterations": 0,
            "final_correct": False,
            "per_iteration": [],
        }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(agent_url, json={
                "question": question["question"],
                "db": db_id,
                "tags": {"eval": "true", "db_id": db_id},
            })
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:  # noqa: BLE001
        return {
            "question": question["question"],
            "db_id": db_id,
            "gold_sql": gold_sql,
            "error": f"agent call failed: {type(e).__name__}: {e}",
            "agent_sql": None,
            "iterations": 0,
            "final_correct": False,
            "per_iteration": [],
        }

    history = payload.get("history", [])
    sql_by_iter: list[str] = []
    for entry in history:
        if entry.get("node") in {"generate_sql", "revise"} and entry.get("sql"):
            sql_by_iter.append(entry["sql"])

    final_sql = payload.get("sql", "")
    if not sql_by_iter and final_sql:
        sql_by_iter = [final_sql]

    per_iteration: list[dict] = []
    last_correct = False
    for i, sql in enumerate(sql_by_iter):
        ok_pred, pred_rows, pred_err = run_sql(db_id, sql)
        correct = matches(gold_rows, pred_rows) if ok_pred else False
        last_correct = correct
        per_iteration.append({
            "iteration": i,
            "sql": sql,
            "correct": correct,
            "error": pred_err,
        })

    return {
        "question": question["question"],
        "db_id": db_id,
        "gold_sql": gold_sql,
        "agent_sql": final_sql,
        "iterations": payload.get("iterations", len(sql_by_iter)),
        "final_correct": last_correct,
        "per_iteration": per_iteration,
        "agent_ok": payload.get("ok", False),
        "agent_error": payload.get("error"),
        "history": history,
    }


def summarize(results: list[dict]) -> dict:
    """Aggregate per-question results with per-iteration carry-forward."""
    n = len(results)
    if n == 0:
        return {
            "total": 0,
            "overall_pass_rate": 0.0,
            "per_iteration_pass_rate": {},
        }

    max_iters = max((len(r.get("per_iteration", [])) for r in results), default=0)
    per_iter_rates: dict[str, float] = {}

    for k in range(max_iters):
        correct = 0
        for r in results:
            per = r.get("per_iteration", [])
            if not per:
                continue
            idx = min(k, len(per) - 1)
            if per[idx]["correct"]:
                correct += 1
        per_iter_rates[str(k)] = correct / n

    final_correct = sum(1 for r in results if r.get("final_correct"))
    return {
        "total": n,
        "overall_pass_rate": final_correct / n,
        "per_iteration_pass_rate": per_iter_rates,
        "errors": sum(1 for r in results if r.get("error")),
    }


# ---------- Main (provided) --------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_FILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_FILE)
    parser.add_argument("--agent-url", default=AGENT_URL_DEFAULT)
    args = parser.parse_args()

    questions = [json.loads(line) for line in args.eval_set.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(questions)} eval questions from {args.eval_set}")

    results: list[dict] = []
    t0 = time.monotonic()
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['db_id']}: {q['question'][:60]}...", flush=True)
        results.append(eval_one(q, args.agent_url))
    elapsed = time.monotonic() - t0

    summary = summarize(results)
    out = {
        "summary": summary,
        "wall_clock_seconds": elapsed,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
