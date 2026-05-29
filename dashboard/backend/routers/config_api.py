"""Config endpoints: stage-policies, model-aliases, review-roster, cron."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import (
    CronPayload,
    ModelAliasesPayload,
    ModelsConfigResponse,
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

@router.get("/models", response_model=ModelsConfigResponse)
def get_model_aliases(_auth=Depends(require_auth)):
    return config_service.get_models_config()


@router.put("/models/aliases")
def set_model_aliases(body: ModelAliasesPayload, _auth=Depends(require_auth)):
    try:
        config_service.set_model_aliases(body.routing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


# --- Review Roster ---

@router.get("/roster")
def get_roster(_auth=Depends(require_auth)):
    return {"roster": config_service.get_roster()}


@router.put("/roster")
def set_roster(body: RosterPayload, _auth=Depends(require_auth)):
    roster = body.roster if body.roster is not None else body.reviewers or []
    try:
        config_service.set_roster(roster)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


# --- Reviewers (alias for roster — FE calls /api/config/reviewers) ---

@router.get("/reviewers")
def get_reviewers(_auth=Depends(require_auth)):
    return {"reviewers": config_service.get_roster()}


@router.put("/reviewers")
def set_reviewers(body: RosterPayload, _auth=Depends(require_auth)):
    reviewers = body.reviewers if body.reviewers is not None else body.roster or []
    try:
        config_service.set_roster(reviewers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}


# --- Cron (bulk — legacy route kept for backward compat) ---

@router.get("/cron")
def get_cron_legacy(_auth=Depends(require_auth)):
    return {"jobs": config_service.get_cron_config()}


@router.put("/cron")
def set_cron(body: CronPayload, _auth=Depends(require_auth)):
    try:
        config_service.set_cron_config(body.jobs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True}
