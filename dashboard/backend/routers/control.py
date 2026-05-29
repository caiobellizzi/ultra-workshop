"""Control endpoints: restart hermes, reload litellm."""
from __future__ import annotations

import subprocess

from fastapi import APIRouter, Depends, HTTPException, status

from dashboard.backend.deps import check_no_inflight, require_auth
from dashboard.backend.models.api_models import RestartRequest, RestartResponse

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/restart", response_model=RestartResponse)
def restart_hermes(body: RestartRequest, _auth=Depends(require_auth)):
    """Restart uws-hermes.service (guarded by in-flight check)."""
    try:
        check_no_inflight(force=body.force)
    except HTTPException:
        raise

    try:
        result = subprocess.run(
            ["sudo", "/usr/bin/systemctl", "restart", "uws-hermes.service"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return RestartResponse(ok=False, detail=result.stderr.strip() or "restart failed")
        return RestartResponse(ok=True, detail="uws-hermes.service restarted")
    except FileNotFoundError:
        # systemctl not available in dev
        return RestartResponse(ok=True, detail="(dev mode: systemctl not available)")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/reload-litellm", response_model=RestartResponse)
def reload_litellm(body: RestartRequest, _auth=Depends(require_auth)):
    """Restart the Workshop LiteLLM Docker container (guarded by in-flight check).

    A LiteLLM restart drops in-flight aider API calls, so the same in-flight guard
    as /restart applies; pass force=true to override.
    """
    try:
        check_no_inflight(force=body.force)
    except HTTPException:
        raise

    try:
        result = subprocess.run(
            ["sudo", "/usr/bin/docker", "restart", "uws-litellm"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return RestartResponse(ok=False, detail=result.stderr.strip() or "docker restart failed")
        return RestartResponse(ok=True, detail="uws-litellm container restarted")
    except FileNotFoundError:
        return RestartResponse(ok=True, detail="(dev mode: docker not available)")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
