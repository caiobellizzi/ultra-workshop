"""Config endpoints: stage-policies, model-aliases, review-roster, cron."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import (
    CronPayload,
    ModelAliasesPayload,
    RosterPayload,
    StagePoliciesPayload,
)
from dashboard.backend.services import config_service

router = APIRouter(prefix="/api/config", tags=["config"])


# --- Stage Policies ---

@router.get("/stage-policies")
def get_stage_policies(_auth=Depends(require_auth)):
    return {"stage_policies": config_service.get_stage_policies()}


@router.put("/stage-policies")
def set_stage_policies(body: StagePoliciesPayload, _auth=Depends(require_auth)):
    try:
        config_service.set_stage_policies(body.stage_policies)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


# --- Model Aliases ---

@router.get("/models")
def get_model_aliases(_auth=Depends(require_auth)):
    return {"model_aliases": config_service.get_model_aliases()}


@router.put("/models")
def set_model_aliases(body: ModelAliasesPayload, _auth=Depends(require_auth)):
    try:
        config_service.set_model_aliases(body.model_aliases)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


# --- Review Roster ---

@router.get("/roster")
def get_roster(_auth=Depends(require_auth)):
    return {"reviewers": config_service.get_roster()}


@router.put("/roster")
def set_roster(body: RosterPayload, _auth=Depends(require_auth)):
    try:
        config_service.set_roster(body.reviewers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


# --- Cron ---

@router.get("/cron")
def get_cron(_auth=Depends(require_auth)):
    return {"jobs": config_service.get_cron_config()}


@router.put("/cron")
def set_cron(body: CronPayload, _auth=Depends(require_auth)):
    try:
        config_service.set_cron_config(body.jobs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}
