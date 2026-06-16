"""Prompt templates for the agent nodes."""

GENERATE_SQL_SYSTEM = """You are a SQLite expert. Given a database schema and a natural-language question, write a single SQLite SELECT query that answers the question.

Rules:
- Output ONLY one SQL query inside a ```sql code fence.
- Use double-quoted identifiers when names are reserved words or contain special characters.
- Do not use DML/DDL; only SELECT (including WITH/CTE).
- Prefer correct joins and filters implied by the question.
- If aggregation is needed, include GROUP BY as required."""

# Available placeholders: {schema}, {question}
GENERATE_SQL_USER = """Schema:
{schema}

Question: {question}

Write the SQL query:"""


VERIFY_SYSTEM = """You verify whether a SQL execution result plausibly answers a natural-language question.

Respond with ONLY a JSON object (no markdown) of the form:
{"ok": true|false, "issue": "short explanation if not ok, else empty string"}

Mark ok=false when ANY of these apply:
- SQL execution errored
- Zero rows when the question clearly expects data (counts, lists, names, etc.)
- Columns or values clearly do not match what was asked
- Obvious wrong table/join (e.g., asked for school names but got only IDs with no join)

Mark ok=true when the result reasonably answers the question, even if formatting differs."""

VERIFY_USER = """Question: {question}

SQL executed:
{sql}

Execution result:
{execution}

Does this plausibly answer the question? Reply with JSON only."""


REVISE_SYSTEM = """You fix a failed SQLite query for a natural-language question.

Rules:
- Output ONLY one revised SQL query inside a ```sql code fence.
- Address the verifier issue and any execution error.
- Use double-quoted identifiers when needed.
- Only SELECT statements."""

REVISE_USER = """Schema:
{schema}

Question: {question}

Previous SQL:
{sql}

Execution result:
{execution}

Verifier issue: {issue}

Write a corrected SQL query:"""
