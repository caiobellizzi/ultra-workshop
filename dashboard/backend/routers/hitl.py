"""HITL endpoints: list pending, resolve."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import HitlResolveRequest, HitlRow
from dashboard.backend.services import hitl_service
from workshop.ledger import validate_task_id

router = APIRouter(prefix="/api/hitl", tags=["hitl"])


@router.get("", response_model=list[HitlRow])
def list_hitl(_auth=Depends(require_auth)):
    rows = hitl_service.list_pending()
    result = []
    for r in rows:
        result.append(
            HitlRow(
                id=r.get("id", 0),
                session_id=r.get("session_id", ""),
                message_id=r.get("message_id"),
                task_description=r.get("task_description", ""),
                created_at=str(r.get("created_at", "")),
                status=r.get("status", "pending"),
                telegram_chat_id=r.get("telegram_chat_id", ""),
                telegram_message_id=r.get("telegram_message_id"),
            )
        )
    return result


@router.post("/{row_id}/resolve", status_code=202)
async def resolve_hitl(row_id: int, body: HitlResolveRequest, _auth=Depends(require_auth)):
    try:
        validate_task_id(body.task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result = await hitl_service.resolve_hitl(
        row_id=row_id,
        task_id=body.task_id,
        hitl_type=body.hitl_type,
        choice=body.choice,
    )
    return result
