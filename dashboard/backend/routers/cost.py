"""Cost endpoints: daily totals, role spend, model spend, per-task spend."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.deps import require_auth
from dashboard.backend.services import cost_service

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get("/daily")
def cost_daily(_auth=Depends(require_auth)):
    return cost_service.get_daily_totals()


@router.get("/roles")
def cost_roles(_auth=Depends(require_auth)):
    return cost_service.get_roles_spend()


@router.get("/models")
def cost_models(_auth=Depends(require_auth)):
    return cost_service.get_model_totals()


@router.get("/task/{task_id}")
def cost_task(task_id: str, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return cost_service.get_task_spend(task_id)
