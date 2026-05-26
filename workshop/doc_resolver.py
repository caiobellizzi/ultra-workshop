"""doc_resolver — 3-tier document resolution for the workshop planner.

Tier 1: workspace_dir (cloned repo) — repo-first, fastest
Tier 2: vault path (VPS second-brain) — offline-capable
Tier 3: Brain HTTP (semantic search) — degraded when Brain has errors

Security: doc_name is validated against path-traversal before any filesystem access.
ASVS V5.1.1: reject ".." components, leading "/", and null bytes.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union

# Tier 3 is optional — only available on VPS where hermes-skills is on sys.path.
try:
    from brain_http import call_agent as _call_agent  # type: ignore[import]
    _BRAIN_AVAILABLE = True
except ImportError:
    _BRAIN_AVAILABLE = False
    _call_agent = None  # type: ignore[assignment]

VAULT_VPS_PATH = os.environ.get("VAULT_VPS_PATH", "/srv/second-brain")


def _validate_doc_name(doc_name: str) -> None:
    """Raise ValueError if doc_name contains path-traversal characters."""
    if not doc_name:
        raise ValueError("unsafe doc_name: empty string")
    if "\x00" in doc_name:
        raise ValueError("unsafe doc_name: contains null byte")
    if doc_name.startswith("/"):
        raise ValueError("unsafe doc_name: absolute path not allowed")
    parts = Path(doc_name).parts
    if ".." in parts:
        raise ValueError(f"unsafe doc_name: path traversal detected in {doc_name!r}")


def _read_first_confined_match(root: Path, doc_name: str) -> str | None:
    """Return the first matching doc whose resolved path stays under root."""
    try:
        root_path = root.resolve()
        if not root_path.exists():
            return None
        for candidate in root_path.rglob(doc_name):
            try:
                resolved = candidate.resolve()
                resolved.relative_to(root_path)
                return resolved.read_text(encoding="utf-8")
            except (OSError, PermissionError, ValueError):
                continue
    except (OSError, PermissionError):
        return None
    return None


def resolve_doc(
    doc_name: str,
    workspace_dir: Union[str, Path, None] = None,
    vault_dir: Union[str, Path, None] = None,
    brain_error: bool = False,
) -> str | None:
    """Resolve a document by name using 3-tier lookup.

    Args:
        doc_name:      Filename to search for (e.g. "prd.md"). Must not contain "..".
        workspace_dir: Cloned repo directory (tier 1). Pass Path or str.
        vault_dir:     Vault root to search (tier 2). Overrides VAULT_VPS_PATH env var.
        brain_error:   If True, skip tier 3 (used in tests to simulate Brain degraded).

    Returns:
        File contents as str, or None if all tiers exhausted.

    Raises:
        ValueError: If doc_name contains path-traversal characters.
    """
    _validate_doc_name(doc_name)

    # Tier 1 — workspace (cloned repo)
    if workspace_dir is not None:
        result = _read_first_confined_match(Path(workspace_dir), doc_name)
        if result is not None:
            return result

    # Tier 2 — vault
    effective_vault = Path(vault_dir) if vault_dir is not None else Path(VAULT_VPS_PATH)
    result = _read_first_confined_match(effective_vault, doc_name)
    if result is not None:
        return result

    # Tier 3 — Brain HTTP (optional, skipped when brain_error=True or not importable)
    if not brain_error and _BRAIN_AVAILABLE and _call_agent is not None:
        try:
            result = _call_agent("query", f"find document: {doc_name}")
            return result.get("content") or None
        except Exception:
            return None

    return None
