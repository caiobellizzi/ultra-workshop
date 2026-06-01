"""Task endpoints: list, get, progress, launch, fix."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import (
    FixRequest,
    LaunchRequest,
    LaunchResponse,
    ProgressResponse,
    TaskDetail,
    TaskListResponse,
    TaskSummary,
)
from dashboard.backend.services import build_trigger, task_store

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_tasks(_auth=Depends(require_auth)):
    return TaskListResponse(tasks=task_store.list_tasks())


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        return task_store.get_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"task {task_id!r} not found")


@router.get("/{task_id}/progress", response_model=ProgressResponse)
def get_progress(task_id: str, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ProgressResponse(events=task_store.get_progress(task_id))


@router.post("", response_model=LaunchResponse, status_code=202)
def launch_task(body: LaunchRequest, _auth=Depends(require_auth)):
    task_id = str(uuid.uuid4()).replace("-", "")[:16]
    # Seed state.json before spawning so the task is immediately visible,
    # even if the subprocess fails before writing its own state.
    try:
        from workshop.state import new_task_state, save_task_state
        save_task_state(new_task_state(
            task_id,
            goal=body.goal,
            repo=body.repo,
            branch=body.branch,
            model_alias=body.model_alias,
            skill_profile=body.skill_profile,
            run_optional_reviewers=body.run_optional_reviewers,
            dry_run=body.dry_run,
        ))
    except Exception:
        pass
    build_trigger.launch_build(
        task_id=task_id,
        repo=body.repo,
        goal=body.goal,
        brainstorm=body.brainstorm,
        branch=body.branch,
        model_alias=body.model_alias,
        skill_profile=body.skill_profile,
        run_optional_reviewers=body.run_optional_reviewers,
        dry_run=body.dry_run,
    )
    return LaunchResponse(task_id=task_id)


@router.post("/{task_id}/fix", status_code=202)
def fix_task(task_id: str, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    build_trigger.launch_fix(task_id)
    return {"ok": True, "task_id": task_id}
