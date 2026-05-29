"""Cron endpoints — /api/cron prefix (FE-facing, separate from /api/config/cron)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import CronJobModel
from dashboard.backend.services import config_service

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("", response_model=dict[str, list[CronJobModel]])
def get_cron(_auth=Depends(require_auth)):
    raw_jobs = config_service.get_cron_config()
    jobs = [CronJobModel(**j) if isinstance(j, dict) else j for j in raw_jobs]
    return {"jobs": jobs}


@router.put("/{name}")
def update_cron_job(name: str, body: dict[str, Any], _auth=Depends(require_auth)):
    raw_jobs = config_service.get_cron_config()
    updated = False
    for job in raw_jobs:
        if isinstance(job, dict) and job.get("name") == name:
            job.update(body)
            updated = True
            break
    if not updated:
        raise HTTPException(status_code=404, detail=f"Cron job {name!r} not found")
    try:
        config_service.set_cron_config(raw_jobs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


@router.post("/{name}/trigger")
def trigger_cron_job(name: str, _auth=Depends(require_auth)):
    # Stub — returns ok:true; hook into scheduler when one is wired up
    return {"ok": True}
