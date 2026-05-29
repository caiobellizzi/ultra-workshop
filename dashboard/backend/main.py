"""Dashboard backend — FastAPI application factory + lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dashboard.backend.config import settings
from dashboard.backend.routers import (
    auth,
    config_api,
    control,
    cost,
    cron,
    health,
    hitl,
    internal,
    repos,
    skills,
    sse,
    tasks,
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: warm the config-loader cache so the first request is fast."""
    try:
        from workshop._config_loader import load_model_aliases, load_stage_policies
        load_stage_policies()
        load_model_aliases()
    except Exception:
        pass  # non-fatal — loader will fall back to hardcoded dicts
    if settings.cookie_secret == "dev-secret-change-me":
        import sys as _sys
        print(
            "[uws-dashboard] WARNING: UWS_DASH_COOKIE_SECRET is the insecure default — "
            "set a real secret before exposing the dashboard.",
            file=_sys.stderr,
            flush=True,
        )
    yield
    # Shutdown — nothing to clean up currently


def create_app() -> FastAPI:
    application = FastAPI(
        title="Ultra-Workshop Dashboard",
        description="Observability + control plane for the ultra-workshop agent pipeline.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Routers
    application.include_router(auth.router)
    application.include_router(tasks.router)
    application.include_router(cost.router)
    application.include_router(config_api.router)
    application.include_router(cron.router)
    application.include_router(skills.router)
    application.include_router(hitl.router)
    application.include_router(control.router)
    application.include_router(repos.router)
    application.include_router(sse.router)
    application.include_router(health.router)
    application.include_router(internal.router)  # no auth — loopback only

    # Serve the built frontend SPA with client-side-routing fallback.
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            application.mount(
                "/assets", StaticFiles(directory=str(assets_dir)), name="assets"
            )
        index_file = frontend_dist / "index.html"

        @application.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            # Unmatched API paths must 404, not return the SPA shell.
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")
            candidate = frontend_dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(index_file))

    return application


app = create_app()
