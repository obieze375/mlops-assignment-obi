#!/usr/bin/env python3
"""Smoke-test Langfuse connectivity from the VM host (Phase 4)."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
sk = os.getenv("LANGFUSE_SECRET_KEY", "")
host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

print("=== Langfuse env ===")
print(f"LANGFUSE_HOST={host}")
print(f"LANGFUSE_PUBLIC_KEY={pk[:16]}..." if pk else "LANGFUSE_PUBLIC_KEY=(missing)")
print(f"LANGFUSE_SECRET_KEY={'set' if sk else '(missing)'}")

if not pk or not sk:
    print("\nFAIL: set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
    sys.exit(1)

if pk.startswith("sk-"):
    print("\nWARN: PUBLIC_KEY looks like a secret key (starts with sk-). Keys may be swapped.")
if sk.startswith("pk-"):
    print("\nWARN: SECRET_KEY looks like a public key (starts with pk-). Keys may be swapped.")

from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

client = get_client()
try:
    ok = client.auth_check()
    print(f"\nauth_check: {ok}")
except Exception as e:  # noqa: BLE001
    print(f"\nauth_check FAILED: {e}")
    print("Common fix: LANGFUSE_HOST=http://localhost:3001 on the VM")
    sys.exit(1)

model = os.getenv("VLLM_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")
base = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
handler = CallbackHandler()
llm = ChatOpenAI(
    model=model,
    base_url=base,
    api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
    temperature=0.0,
)

print("\nSending one traced LLM call...")
llm.invoke([HumanMessage(content="Reply with exactly: langfuse ok")], config={"callbacks": [handler]})
client.flush()
print("Done. Open Langfuse UI -> Traces (http://localhost:3001)")
