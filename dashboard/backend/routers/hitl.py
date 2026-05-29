"""HITL endpoints: list pending, resolve."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import HITLItem, HITLListResponse, HitlResolveRequest
from dashboard.backend.services import hitl_service
from workshop.ledger import validate_task_id

router = APIRouter(prefix="/api/hitl", tags=["hitl"])

# Status → hitl_type mapping
_HITL_STATUS_TYPE: dict[str, str] = {
    "needs_clarification": "clarification",
    "needs_approval": "approval",
    "needs_timeout_recovery": "timeout",
    "needs_review_recovery": "review",
    "needs_step_recovery": "step",
}


def _build_session_map() -> dict[str, dict[str, Any]]:
    """Return {session_id: state_data} for all tasks that have a session_id."""
    base = Path(settings.tasks_base)
    mapping: dict[str, dict[str, Any]] = {}
    if not base.exists():
        return mapping
    for state_file in base.glob("*/state.json"):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            sid = str(data.get("session_id", ""))
            if sid:
                mapping[sid] = data
        except Exception:
            continue
    return mapping


def _payload_for_state(data: dict[str, Any], hitl_type: str) -> dict[str, Any]:
    """Extract the relevant HITL payload from task state."""
    if hitl_type == "clarification":
        clarifications = data.get("clarifications", [])
        if clarifications:
            last = clarifications[-1]
            return last if isinstance(last, dict) else {"message": str(last)}
        return {}
    if hitl_type == "approval":
        ap = data.get("approval_payload")
        return ap if isinstance(ap, dict) and ap else {}
    if hitl_type == "timeout":
        tp = data.get("timeout_payload")
        return tp if isinstance(tp, dict) and tp else {}
    return {}


@router.get("", response_model=HITLListResponse)
def list_hitl(_auth=Depends(require_auth)):
    rows = hitl_service.list_pending()
    session_map = _build_session_map()
    items: list[HITLItem] = []
    for r in rows:
        session_id = r.get("session_id", "")
        state = session_map.get(session_id, {})
        task_id = str(state.get("task_id", session_id))
        status = str(state.get("status", ""))
        hitl_type = _HITL_STATUS_TYPE.get(status, "unknown")
        payload = _payload_for_state(state, hitl_type)
        items.append(
            HITLItem(
                task_id=task_id,
                hitl_type=hitl_type,
                payload=payload,
                created_at=str(r.get("created_at", "")),
            )
        )
    return HITLListResponse(items=items)


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
