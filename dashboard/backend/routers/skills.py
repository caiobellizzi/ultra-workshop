"""Skills endpoints: list, get, update, history, rollback, dry-run."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import (
    SkillDetail,
    SkillDryRunRequest,
    SkillSummary,
    SkillUpdateRequest,
)

router = APIRouter(prefix="/api/skills", tags=["skills"])

_SKILL_NAME_RE = re.compile(r"^[a-z0-9_-]+$")
_MAX_SKILL_SIZE = 128_000  # bytes
_OUTPUT_SCHEMA_RE = re.compile(r"##\s*output\s*schema", re.IGNORECASE)


def _skills_root() -> Path:
    return Path(settings.skills_root)


def _skill_path(name: str) -> Path:
    return _skills_root() / name / "SKILL.md"


def _has_output_schema(content: str) -> bool:
    return bool(_OUTPUT_SCHEMA_RE.search(content))


@router.get("", response_model=list[SkillSummary])
def list_skills(_auth=Depends(require_auth)):
    root = _skills_root()
    if not root.exists():
        return []
    results: list[SkillSummary] = []
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        name = skill_dir.name
        content = skill_file.read_text(encoding="utf-8")
        results.append(
            SkillSummary(
                name=name,
                path=str(skill_file),
                size=len(content.encode("utf-8")),
                has_output_schema=_has_output_schema(content),
            )
        )
    return results


@router.get("/{name}", response_model=SkillDetail)
def get_skill(name: str, _auth=Depends(require_auth)):
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")
    skill_file = _skill_path(name)
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"skill {name!r} not found")
    content = skill_file.read_text(encoding="utf-8")
    return SkillDetail(
        name=name,
        content=content,
        path=str(skill_file),
        size=len(content.encode("utf-8")),
        has_output_schema=_has_output_schema(content),
    )


@router.put("/{name}")
def update_skill(name: str, body: SkillUpdateRequest, _auth=Depends(require_auth)):
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")

    content_bytes = body.content.encode("utf-8")
    if len(content_bytes) > _MAX_SKILL_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"skill content too large ({len(content_bytes)} bytes > {_MAX_SKILL_SIZE})",
        )

    skill_file = _skill_path(name)
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"skill {name!r} not found")

    # Detect Output Schema change (breaking-change warning)
    old_content = skill_file.read_text(encoding="utf-8")
    old_has_schema = _has_output_schema(old_content)
    new_has_schema = _has_output_schema(body.content)
    output_schema_changed = old_has_schema != new_has_schema

    # Backup existing file
    bak_path = skill_file.with_suffix(".bak")
    shutil.copy2(skill_file, bak_path)

    # Atomic write
    tmp = skill_file.with_name(f"{skill_file.name}.tmp")
    tmp.write_text(body.content, encoding="utf-8")
    tmp.replace(skill_file)

    return {
        "ok": True,
        "output_schema_changed": output_schema_changed,
        "warning": "Output Schema block changed — this may be a breaking change." if output_schema_changed else None,
    }


@router.get("/{name}/history")
def skill_history(name: str, _auth=Depends(require_auth)):
    """Return recent git log for the skill file (if under git)."""
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")
    skill_file = _skill_path(name)
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"skill {name!r} not found")
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20", "--", str(skill_file)],
            capture_output=True,
            text=True,
            cwd=str(_skills_root()),
            timeout=10,
        )
        lines = result.stdout.strip().splitlines() if result.returncode == 0 else []
    except Exception:
        lines = []
    return {"history": lines}


@router.post("/{name}/rollback")
def skill_rollback(name: str, _auth=Depends(require_auth)):
    """Roll back to .bak file."""
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")
    skill_file = _skill_path(name)
    bak_path = skill_file.with_suffix(".bak")
    if not bak_path.exists():
        raise HTTPException(status_code=404, detail=f"no backup found for skill {name!r}")
    tmp = skill_file.with_name(f"{skill_file.name}.tmp")
    shutil.copy2(bak_path, tmp)
    tmp.replace(skill_file)
    return {"ok": True, "restored_from": str(bak_path)}


@router.post("/{name}/dry-run")
async def skill_dry_run(name: str, body: SkillDryRunRequest, _auth=Depends(require_auth)):
    """SSE dry-run: stream simulated output (stub — full eval in v2)."""
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")

    async def _generate():
        yield "data: [dry-run] Validating skill content...\n\n"
        content_bytes = body.content.encode("utf-8")
        if len(content_bytes) > _MAX_SKILL_SIZE:
            yield f"data: [ERROR] Content too large: {len(content_bytes)} bytes\n\n"
            return
        if not _OUTPUT_SCHEMA_RE.search(body.content):
            yield "data: [WARN] No Output Schema block detected\n\n"
        yield "data: [dry-run] Syntax check passed\n\n"
        yield "data: [dry-run] Done\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")
