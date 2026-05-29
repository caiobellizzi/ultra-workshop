"""Config service — validated atomic reads/writes for YAML config files.

Manages: stage-policies, model-aliases, review-roster, cron schedule.
All writes are atomic (tmp + os.replace pattern from workshop/state.py).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from dashboard.backend.config import settings

# ---------------------------------------------------------------------------
# Required stages for validation
# ---------------------------------------------------------------------------
REQUIRED_STAGES = {"brainstorm", "triage", "requirements", "planner", "coder", "reviewer"}

# ---------------------------------------------------------------------------
# Required reviewer roles (security + correctness always-on)
# ---------------------------------------------------------------------------
REQUIRED_REVIEWERS = {"security", "correctness"}


def _hermes_config_dir() -> Path:
    return Path(settings.hermes_config_dir)


def _atomic_write_yaml(path: Path, data: Any) -> None:
    """Write *data* as YAML to *path* atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    tmp.replace(path)


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Stage policies
# ---------------------------------------------------------------------------

def get_stage_policies() -> dict[str, Any]:
    data = _read_yaml(_hermes_config_dir() / "stage-policies.yaml")
    if data is None:
        return {}
    return data.get("stage_policies", {})


def set_stage_policies(policies: dict[str, Any]) -> None:
    """Validate and write stage_policies section.

    Raises ValueError if any required stage is missing or data is malformed.
    """
    missing = REQUIRED_STAGES - set(policies.keys())
    if missing:
        raise ValueError(f"stage-policies write rejected: missing stages {sorted(missing)}")

    for stage, raw in policies.items():
        if not isinstance(raw, dict):
            raise ValueError(f"stage {stage!r}: policy must be a dict, got {type(raw).__name__}")
        timeout = raw.get("timeout")
        if timeout is not None and not isinstance(timeout, (int, float)):
            raise ValueError(f"stage {stage!r}: timeout must be numeric")

    yaml_path = _hermes_config_dir() / "stage-policies.yaml"
    current = _read_yaml(yaml_path) or {}
    current["stage_policies"] = policies
    _atomic_write_yaml(yaml_path, current)

    # Invalidate the loader cache so the next request reflects the new values
    try:
        from workshop._config_loader import invalidate_cache
        invalidate_cache()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Model aliases
# ---------------------------------------------------------------------------

def get_model_aliases() -> dict[str, str]:
    data = _read_yaml(_hermes_config_dir() / "stage-policies.yaml")
    if data is None:
        return {}
    return data.get("model_aliases", {})


def get_models_config() -> dict[str, Any]:
    """Return structured {aliases, routing} for GET /api/config/models.

    - aliases: list of ModelAliasDef built from deploy/litellm/config.yaml
    - routing: list of AgentRouting built from stage-policies.yaml model_aliases
    """
    # Build aliases from LiteLLM config
    repo_root = Path(__file__).parent.parent.parent.parent
    litellm_config_path = repo_root / "deploy" / "litellm" / "config.yaml"
    aliases: list[dict[str, Any]] = []
    if litellm_config_path.exists():
        try:
            litellm_data = yaml.safe_load(litellm_config_path.read_text(encoding="utf-8"))
            for entry in litellm_data.get("model_list") or []:
                model_name = entry.get("model_name", "")
                params = entry.get("litellm_params", {})
                raw_model = params.get("model", "")
                # provider/model_id split: "openai/some/model" → provider="openai", model_id="some/model"
                if "/" in raw_model:
                    provider, model_id = raw_model.split("/", 1)
                else:
                    provider, model_id = "", raw_model
                timeout = params.get("timeout") or params.get("request_timeout")
                retries = params.get("max_retries")
                aliases.append({
                    "alias": model_name,
                    "provider": provider,
                    "model_id": model_id,
                    "timeout": timeout,
                    "retries": retries,
                    "fallback": None,
                })
        except Exception:
            pass

    # Build routing from stage-policies.yaml model_aliases
    model_aliases_map = get_model_aliases()
    routing: list[dict[str, Any]] = [
        {"agent": agent, "alias": alias}
        for agent, alias in model_aliases_map.items()
    ]

    return {"aliases": aliases, "routing": routing}


def _get_litellm_model_names() -> set[str]:
    """Read deploy/litellm/config.yaml and return the set of model_name values."""
    repo_root = Path(__file__).parent.parent.parent.parent
    litellm_config = repo_root / "deploy" / "litellm" / "config.yaml"
    if not litellm_config.exists():
        return set()
    try:
        data = yaml.safe_load(litellm_config.read_text(encoding="utf-8"))
        return {entry["model_name"] for entry in (data.get("model_list") or []) if "model_name" in entry}
    except Exception:
        return set()


def set_model_aliases(aliases: dict[str, str]) -> None:
    """Validate and write model_aliases section.

    Each alias value is cross-checked against the LiteLLM model_list names.
    Raises ValueError on unknown alias targets.
    """
    known_models = _get_litellm_model_names()
    if known_models:
        unknown = {v for v in aliases.values() if v not in known_models}
        if unknown:
            raise ValueError(
                f"model-aliases write rejected: unknown LiteLLM model targets: {sorted(unknown)}"
            )

    yaml_path = _hermes_config_dir() / "stage-policies.yaml"
    current = _read_yaml(yaml_path) or {}
    current["model_aliases"] = aliases
    _atomic_write_yaml(yaml_path, current)

    try:
        from workshop._config_loader import invalidate_cache
        invalidate_cache()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Review roster
# ---------------------------------------------------------------------------

def get_roster() -> list[dict[str, Any]]:
    data = _read_yaml(_hermes_config_dir() / "review-roster.yaml")
    if data is None:
        return []
    return data.get("reviewers", [])


def set_roster(reviewers: list[dict[str, Any]]) -> None:
    """Validate and write review-roster.yaml.

    Requires security and correctness reviewers to be present.
    """
    roles = {r.get("role") for r in reviewers}
    missing = REQUIRED_REVIEWERS - roles
    if missing:
        raise ValueError(f"roster write rejected: required reviewers {sorted(missing)} must be present")

    yaml_path = _hermes_config_dir() / "review-roster.yaml"
    current = _read_yaml(yaml_path) or {}
    current["reviewers"] = reviewers
    _atomic_write_yaml(yaml_path, current)


# ---------------------------------------------------------------------------
# Cron
# ---------------------------------------------------------------------------

def get_cron_config() -> list[dict[str, Any]]:
    """Read cron job definitions from hermes-config/cron.yaml (if exists)."""
    data = _read_yaml(_hermes_config_dir() / "cron.yaml")
    if data is None:
        return []
    return data.get("jobs", [])


def set_cron_config(jobs: list[dict[str, Any]]) -> None:
    """Write cron job definitions."""
    for i, job in enumerate(jobs):
        if not isinstance(job, dict):
            raise ValueError(f"cron job #{i} must be a dict")
    yaml_path = _hermes_config_dir() / "cron.yaml"
    _atomic_write_yaml(yaml_path, {"jobs": jobs})
