from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StagePolicy:
    timeout: int
    tool_timeout: int | None = None
    auto_retries: int = 0
    hitl_on_timeout: bool = False


# ---------------------------------------------------------------------------
# Public accessors — delegate to _config_loader for YAML-backed runtime config
# ---------------------------------------------------------------------------

def stage_model_alias(skill_name: str) -> str:
    """Return the LiteLLM model alias for the given specialist skill name."""
    from workshop._config_loader import load_model_aliases
    return load_model_aliases().get(skill_name, "default-worker")


def stage_policy(stage: str) -> StagePolicy:
    from workshop._config_loader import load_stage_policies
    policies = load_stage_policies()
    try:
        return policies[stage]
    except KeyError as exc:
        known_stages = ", ".join(sorted(policies))
        raise KeyError(f"no policy defined for stage {stage!r}; known stages: {known_stages}") from exc


def stage_timeout(stage: str) -> int:
    return stage_policy(stage).timeout


def stage_tool_timeout(stage: str) -> int | None:
    return stage_policy(stage).tool_timeout
