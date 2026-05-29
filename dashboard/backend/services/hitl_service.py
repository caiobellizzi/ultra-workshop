"""HITL service — reads pending_hitl.db and drives workshop_continue.py."""
from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

from dashboard.backend.config import settings


def _load_startup_hitl_scan():
    """Load the startup-hitl-scan module via importlib (hyphenated filename)."""
    hitl_scan_path = Path(settings.workshop_root) / "hermes-skills" / "startup-hitl-scan.py"
    if not hitl_scan_path.exists():
        # dev fallback: search relative to repo root
        repo_root = Path(__file__).parent.parent.parent.parent
        hitl_scan_path = repo_root / "hermes-skills" / "startup-hitl-scan.py"
    if not hitl_scan_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("startup_hitl_scan", hitl_scan_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def list_pending() -> list[dict[str, Any]]:
    """Return pending HITL rows from pending_hitl.db."""
    mod = _load_startup_hitl_scan()
    if mod is None:
        return []
    db_path = Path(settings.hitl_db)
    try:
        return mod.fetch_pending(db_path=db_path)
    except Exception:
        return []


async def resolve_hitl(row_id: int, task_id: str, hitl_type: str, choice: str) -> dict[str, Any]:
    """Drive workshop_continue.py in a thread; return immediately (202 pattern)."""
    workshop_continue = Path(settings.workshop_continue_py)
    if not workshop_continue.exists():
        # dev fallback
        repo_root = Path(__file__).parent.parent.parent.parent
        workshop_continue = repo_root / "hermes-skills" / "workshop_continue.py"

    if not workshop_continue.exists():
        return {"ok": False, "detail": "workshop_continue.py not found"}

    cmd = [
        sys.executable,
        str(workshop_continue),
        "--task-id", task_id,
        "--hitl-type", hitl_type,
        "--choice", choice,
        "--row-id", str(row_id),
    ]

    def _run_sync() -> dict[str, Any]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return {
                "ok": result.returncode == 0,
                "detail": result.stdout[-500:] if result.stdout else result.stderr[-500:],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "detail": "workshop_continue.py timed out"}
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    return await asyncio.to_thread(_run_sync)
