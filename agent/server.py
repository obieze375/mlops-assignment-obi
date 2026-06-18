"""FastAPI wrapper exposing the agent over HTTP.

Run:
    uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001

The /answer endpoint accepts {question, db, tags?} and returns the
agent's final SQL, the result rows, and per-iteration history.
"""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from agent.graph import AgentState, graph  # noqa: E402

# Langfuse callback handler. If keys are set we initialize it; failures
# are NOT swallowed - a misconfigured Langfuse should not silently
# produce zero traces.
_lf_handler: Any = None
_langfuse_client: Any = None
if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
    from langfuse import get_client
    from langfuse.langchain import CallbackHandler

    _langfuse_client = get_client()
    _lf_handler = CallbackHandler()


app = FastAPI()


class AnswerRequest(BaseModel):
    question: str
    db: str
    tags: dict[str, str] = {}


class AnswerResponse(BaseModel):
    sql: str
    rows: list[list[Any]] | None
    iterations: int
    ok: bool
    error: str | None = None
    history: list[dict[str, Any]] = []


@app.on_event("startup")
def _startup() -> None:
    if _lf_handler is None:
        print("Langfuse: disabled (set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY in .env)")
        return
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    print(f"Langfuse: enabled host={host} public_key={pk[:12]}...")
    if _langfuse_client is not None:
        try:
            ok = _langfuse_client.auth_check()
            print(f"Langfuse: auth_check={ok}")
        except Exception as e:  # noqa: BLE001
            print(f"Langfuse: auth_check failed: {e}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "langfuse": "enabled" if _lf_handler else "disabled"}


@app.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest) -> AnswerResponse:
    state = AgentState(question=req.question, db_id=req.db)
    config: dict[str, Any] = {
        "callbacks": [_lf_handler] if _lf_handler is not None else [],
        "metadata": {
            **req.tags,
            "langfuse_tags": list(req.tags.values()) if req.tags else [],
        },
        "run_name": f"answer:{req.db}",
    }
    try:
        final = graph.invoke(state, config=config)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    finally:
        if _langfuse_client is not None:
            _langfuse_client.flush()

    sql = final.get("sql", "")
    iteration = final.get("iteration", 0)
    history = final.get("history", [])
    execution = final.get("execution")

    if execution is None:
        return AnswerResponse(
            sql=sql,
            rows=None,
            iterations=iteration,
            ok=False,
            error="agent produced no execution result",
            history=history,
        )
    if not execution.ok:
        return AnswerResponse(
            sql=sql,
            rows=None,
            iterations=iteration,
            ok=False,
            error=execution.error,
            history=history,
        )

    return AnswerResponse(
        sql=sql,
        rows=[list(r) for r in (execution.rows or [])],
        iterations=iteration,
        ok=True,
        history=history,
    )
