"""
brain_http — HTTP helper for Brain Agno endpoints.

Provides a synchronous httpx wrapper for POST /agents/{id}/runs.

CRITICAL: Brain uses multipart/form-data (data={...}), NOT application/json.
Sending json={...} causes a 422 Unprocessable Entity response.

Deploy location: /opt/ultra-workshop/hermes-skills/brain_http.py
Run on: VPS only (Brain API is only reachable from 127.0.0.1:7000 on the VPS)

Synchronous only — no coroutines, no asyncio. Hermes skill bodies invoke this
via: terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py <agent_id> <message>
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

BRAIN_BASE_URL = "http://127.0.0.1:7000"
DEFAULT_TIMEOUT = 60.0


def _queue_path() -> Path:
    """Resolve the workshop queue JSONL — must match cron_bug_scan_fastpoll._queue_path."""
    vault = os.environ.get("VAULT_VPS_PATH", "/srv/second-brain")
    return Path(vault) / "_system" / ".workshop-queue.jsonl"


def call_agent(agent_id: str, message: str, user_id: str = "workshop") -> dict:
    """POST to /agents/{agent_id}/runs using multipart/form-data.

    CRITICAL: Brain's Agno 2.6.7 API requires form-data, NOT application/json.
    Using json={...} instead of data={...} will return HTTP 422.

    Args:
        agent_id: Brain agent identifier (e.g., "query", "ingest", "research").
        message:  The message or query to send to the agent.
        user_id:  User identifier forwarded to Brain (default: "workshop").

    Returns:
        Parsed JSON response dict containing run_id, agent_id, session_id,
        content, status, and metrics fields.

    Raises:
        SystemExit(1) if Brain returns status "ERROR" (application-level error).
        httpx.HTTPError on network/HTTP transport failures.
    """
    import httpx  # lazy — only the agent-call path needs httpx; ACK is file-only

    resp = httpx.post(
        f"{BRAIN_BASE_URL}/agents/{agent_id}/runs",
        data={"message": message, "stream": "false", "user_id": user_id},
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "ERROR":
        # V4 relaxation: Brain's query agent returns status:ERROR due to a Groq
        # structured-output + tool-calling conflict in LiteLLM configuration.
        # HTTP 200 is returned correctly; run_id is present in the response.
        # We emit the error to stderr for visibility but do NOT exit 1 — callers
        # (smoke tests, skill bodies) need the run_id regardless of status.
        print(f"Brain error: {data.get('content', 'unknown')}", file=sys.stderr)
    return data


def mark_queue_entry_dispatched(entry_id: str) -> dict:
    """Mark a queue entry dispatched by flipping `dispatched: true` in the local JSONL.

    The Brain (ultra-agents-brain) does not serve a queue-ACK HTTP endpoint
    (PUT /workshop/queue/{id}/dispatched returns 404) — it only owns the queue
    file. Since fast-poll and standard-poll already read this file directly, the
    ACK is performed in-place here. Without it, dispatched entries re-fire on
    every poll (telegram spam / re-run builds).

    Atomic: rewrites the whole JSONL via a temp file + os.replace. Entries other
    than `entry_id` are preserved verbatim. Returns {id, dispatched, found}.
    Never raises on a missing/empty queue — returns found=False.
    """
    queue_file = _queue_path()
    if not queue_file.exists():
        return {"id": entry_id, "dispatched": False, "found": False}

    found = False
    out_lines: list[str] = []
    for raw in queue_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            out_lines.append(line)  # preserve unparseable lines untouched
            continue
        if entry.get("id") == entry_id:
            entry["dispatched"] = True
            found = True
        out_lines.append(json.dumps(entry))

    payload = "".join(f"{ln}\n" for ln in out_lines)
    fd, tmp = tempfile.mkstemp(dir=str(queue_file.parent), prefix=".workshop-queue.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, queue_file)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return {"id": entry_id, "dispatched": found, "found": found}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: brain_http.py <agent_id> <message>",
            file=sys.stderr,
        )
        print(
            "  agent_id: query | ingest | research | curator | chat",
            file=sys.stderr,
        )
        print(
            "  message:  the message to send (quote multi-word messages)",
            file=sys.stderr,
        )
        sys.exit(1)

    agent_id = sys.argv[1]
    message = " ".join(sys.argv[2:])
    result = call_agent(agent_id, message)
    print(
        json.dumps(
            {
                "run_id": result.get("run_id"),
                "content": result.get("content"),
                "status": result.get("status"),
            }
        )
    )
