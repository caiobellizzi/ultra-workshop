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
    GitHistoryEntry,
    SkillDetail,
    SkillDryRunRequest,
    SkillHistoryResponse,
    SkillListResponse,
    SkillMetaModel,
    SkillRollbackRequest,
    SkillSummary,
    SkillUpdateRequest,
)

router = APIRouter(prefix="/api/skills", tags=["skills"])

_SKILL_NAME_RE = re.compile(r"^[a-z0-9_-]+$")
_MAX_SKILL_SIZE = 128_000  # bytes
_OUTPUT_SCHEMA_RE = re.compile(r"##\s*output\s*schema", re.IGNORECASE)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _skills_root() -> Path:
    return Path(settings.skills_root)


def _skill_path(name: str) -> Path:
    return _skills_root() / name / "SKILL.md"


def _has_output_schema(content: str) -> bool:
    return bool(_OUTPUT_SCHEMA_RE.search(content))


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter from a SKILL.md file into a plain dict."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}
    try:
        import yaml  # PyYAML is already a transitive dep via pydantic/fastapi env
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _meta_from_content(name: str, path: str, content: str) -> SkillMetaModel:
    fm = _parse_frontmatter(content)
    version = str(fm.get("version", "")).strip()
    description = str(fm.get("description", "")).strip()
    raw_tags = fm.get("tags", [])
    tags: list[str] = [str(t) for t in raw_tags] if isinstance(raw_tags, list) else []
    return SkillMetaModel(
        name=name,
        version=version,
        description=description,
        tags=tags,
        path=path,
    )


@router.get("", response_model=SkillListResponse)
def list_skills(_auth=Depends(require_auth)):
    root = _skills_root()
    if not root.exists():
        return SkillListResponse(skills=[])
    results: list[SkillSummary] = []
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        name = skill_dir.name
        content = skill_file.read_text(encoding="utf-8")
        meta = _meta_from_content(name, str(skill_file), content)
        results.append(
            SkillSummary(
                name=name,
                version=meta.version,
                description=meta.description,
                tags=meta.tags,
                path=str(skill_file),
                size=len(content.encode("utf-8")),
                has_output_schema=_has_output_schema(content),
            )
        )
    return SkillListResponse(skills=results)


@router.get("/{name}", response_model=SkillDetail)
def get_skill(name: str, _auth=Depends(require_auth)):
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")
    skill_file = _skill_path(name)
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"skill {name!r} not found")
    content = skill_file.read_text(encoding="utf-8")
    meta = _meta_from_content(name, str(skill_file), content)
    return SkillDetail(meta=meta, content=content)


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


@router.get("/{name}/history", response_model=SkillHistoryResponse)
def skill_history(name: str, _auth=Depends(require_auth)):
    """Return recent git log for the skill file (if under git)."""
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")
    skill_file = _skill_path(name)
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"skill {name!r} not found")
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%ai|%s|%an", "-20", "--", str(skill_file)],
            capture_output=True,
            text=True,
            cwd=str(_skills_root()),
            timeout=10,
        )
        raw_lines = result.stdout.strip().splitlines() if result.returncode == 0 else []
    except Exception:
        raw_lines = []

    entries: list[GitHistoryEntry] = []
    for line in raw_lines:
        parts = line.split("|", 3)
        if len(parts) == 4:
            entries.append(
                GitHistoryEntry(
                    hash=parts[0],
                    date=parts[1],
                    message=parts[2],
                    author=parts[3],
                )
            )
    return SkillHistoryResponse(entries=entries)


@router.post("/{name}/rollback")
def skill_rollback(name: str, body: SkillRollbackRequest, _auth=Depends(require_auth)):
    """Roll back a skill to a specific git commit, or to the .bak file if commit is empty."""
    if not _SKILL_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="invalid skill name")
    skill_file = _skill_path(name)

    commit = body.commit.strip()
    if commit:
        # Restore from git history: compute relative path from skills_root
        skills_root = _skills_root()
        try:
            rel_path = skill_file.relative_to(skills_root)
        except ValueError:
            rel_path = Path(name) / "SKILL.md"
        try:
            result = subprocess.run(
                ["git", "show", f"{commit}:{rel_path}"],
                capture_output=True,
                text=True,
                cwd=str(skills_root),
                timeout=10,
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"commit {commit!r} not found or skill not in that commit",
                )
            restored_content = result.stdout
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"git show failed: {exc}") from exc

        # Backup current before overwriting
        bak_path = skill_file.with_suffix(".bak")
        if skill_file.exists():
            shutil.copy2(skill_file, bak_path)

        tmp = skill_file.with_name(f"{skill_file.name}.tmp")
        tmp.write_text(restored_content, encoding="utf-8")
        tmp.replace(skill_file)
        return {"ok": True, "restored_from": commit}
    else:
        # Fallback: restore from .bak file
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
