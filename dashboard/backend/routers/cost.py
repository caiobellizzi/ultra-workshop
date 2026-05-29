"""Cost endpoints: daily totals, role spend, model spend, per-task spend."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import (
    CostSummaryResponse,
    CostTrendsResponse,
    DailySpendResponse,
    ModelSpendResponse,
    RoleCostListResponse,
    RoleSpendResponse,
    TaskCostListResponse,
    TaskCostRowResponse,
    WaveBreakdownItem,
)
from dashboard.backend.services import cost_service

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.get("/summary", response_model=CostSummaryResponse)
def cost_summary(_auth=Depends(require_auth)):
    data = cost_service.get_summary()
    return CostSummaryResponse(**data)


@router.get("/tasks", response_model=TaskCostListResponse)
def cost_tasks(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    _auth=Depends(require_auth),
):
    rows = cost_service.get_tasks_spend(from_date=from_date, to_date=to_date)
    tasks = [
        TaskCostRowResponse(
            task_id=r["task_id"],
            goal=r["goal"],
            repo=r["repo"],
            date=r["date"],
            status=r["status"],
            stage_costs=r["stage_costs"],
            total_cents=r["total_cents"],
            wave_breakdown=[WaveBreakdownItem(**w) for w in r["wave_breakdown"]] or None,
        )
        for r in rows
    ]
    return TaskCostListResponse(tasks=tasks)


@router.get("/trends", response_model=CostTrendsResponse)
def cost_trends(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    _auth=Depends(require_auth),
):
    data = cost_service.get_trends(from_date=from_date, to_date=to_date)
    return CostTrendsResponse(
        daily=[DailySpendResponse(**d) for d in data["daily"]],
        by_model=[ModelSpendResponse(**m) for m in data["by_model"]],
        by_role=[RoleSpendResponse(**r) for r in data["by_role"]],
    )


@router.get("/roles", response_model=RoleCostListResponse)
def cost_roles(_auth=Depends(require_auth)):
    rows = cost_service.get_roles_spend()
    return RoleCostListResponse(
        roles=[RoleSpendResponse(**r) for r in rows]
    )


@router.get("/task/{task_id}", response_model=TaskCostRowResponse)
def cost_task(task_id: str, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    data = cost_service.get_task_spend(task_id)
    return TaskCostRowResponse(
        task_id=data["task_id"],
        goal=data["goal"],
        repo=data["repo"],
        date=data["date"],
        status=data["status"],
        stage_costs=data["stage_costs"],
        total_cents=data["total_cents"],
        wave_breakdown=[WaveBreakdownItem(**w) for w in data["wave_breakdown"]] or None,
    )


@router.get("/daily")
def cost_daily(_auth=Depends(require_auth)):
    return cost_service.get_daily_totals()


@router.get("/models")
def cost_models(_auth=Depends(require_auth)):
    return cost_service.get_model_totals()
