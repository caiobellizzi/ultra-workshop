"""Dashboard backend configuration — Pydantic Settings, env prefix UWS_DASH_."""
from __future__ import annotations

import sys
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _dev_fallback(relative: str) -> str:
    """Return a repo-relative path for local dev when production paths don't exist."""
    repo_root = Path(__file__).parent.parent.parent
    return str(repo_root / relative)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UWS_DASH_", env_file=".env", extra="ignore")

    # --- Service binding ---
    host: str = "127.0.0.1"
    port: int = 7010

    # --- Queue ---
    # Max concurrent tasks the workshop runner will dispatch (Workstream C queue stats).
    max_concurrency: int = 3

    # --- Paths ---
    tasks_base: str = "/home/uws/.ultra-workshop/tasks"
    hitl_db: str = "/home/uws/.ultra-workshop/pending_hitl.db"
    # Dashboard-owned cost database (SQLite)
    spend_db: str = "/home/uws/.ultra-workshop/dashboard/spend.sqlite"
    workshop_root: str = "/opt/ultra-workshop"
    hermes_config_dir: str = "/opt/ultra-workshop/hermes-config"
    cost_ledger_md: str = "/srv/second-brain/_system/cost-ledger.md"
    # skills canonical tree
    skills_root: str = "/opt/ultra-workshop/skills"
    # repo registry
    repo_registry_path: str = "/srv/second-brain/_system/workshop-repos.json"

    # --- Auth ---
    # Single-owner session cookie secret; required in production.
    # In dev, falls back to a dummy value so the server boots.
    cookie_secret: str = "dev-secret-change-me"
    # Optional API token for simple bearer auth
    api_token: str = ""
    # Login password. Kept separate from cookie_secret (the HMAC signing key) so the
    # password can be memorable without weakening cookie signing. Falls back to
    # cookie_secret when unset (backward compatible).
    login_password: str = ""
    # Session cookie name
    session_cookie_name: str = "uws_dash_session"
    # Send the session cookie only over HTTPS (set False only for local HTTP dev)
    secure_cookie: bool = True

    # --- LiteLLM proxy ---
    # Mirrors hermes-config/config.yaml base_url (without /v1 path).
    litellm_base_url: str = "http://127.0.0.1:4000"

    # --- GitHub ---
    # Personal access token for GitHub API calls (read:repo scope required).
    github_pat: str = ""

    # --- Workshop binary paths ---
    workshop_build_py: str = "/opt/ultra-workshop/hermes-skills/workshop_build.py"
    workshop_continue_py: str = "/opt/ultra-workshop/hermes-skills/workshop_continue.py"

    def resolve_paths(self) -> "Settings":
        """Patch VPS-only paths to repo-relative dev fallbacks if they don't exist."""
        mapping = {
            "tasks_base": "tests/phase-11/tmp-tasks",
            "hermes_config_dir": "hermes-config",
            "workshop_root": ".",
            "skills_root": "skills",
        }
        for attr, fallback in mapping.items():
            vps_path = Path(getattr(self, attr))
            if not vps_path.exists():
                object.__setattr__(self, attr, _dev_fallback(fallback))
        return self


# Module-level singleton (resolved once at import time for simplicity;
# can be overridden in tests via dependency injection).
settings = Settings().resolve_paths()
