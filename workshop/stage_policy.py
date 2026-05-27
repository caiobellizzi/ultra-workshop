from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StagePolicy:
    timeout: int
    tool_timeout: int | None = None
    auto_retries: int = 0
    hitl_on_timeout: bool = False


STAGE_POLICIES: dict[str, StagePolicy] = {
    "triage": StagePolicy(timeout=180, auto_retries=1),
    "requirements": StagePolicy(timeout=180, auto_retries=1),
    "planner": StagePolicy(timeout=900, auto_retries=1),
    # coder: UWS_CODER_MAX is the orchestrator backstop for the full multi-step coder
    # stage. Per-step idle timeout + total task budget govern per step; this is the
    # outer wall-clock limit only. hitl_on_timeout=False — recovery ladder fires first.
    "coder": StagePolicy(
        timeout=int(os.environ.get("UWS_CODER_MAX", "7200")),
        tool_timeout=int(os.environ.get("UWS_CODER_MAX", "7200")),
        auto_retries=0,
        hitl_on_timeout=False,
    ),
    "reviewer": StagePolicy(timeout=300, auto_retries=1),
}

# Per-stage model alias routing map.
# Each stage's query payload includes "model_alias": MODEL_ALIASES.get(stage, "default-worker")
# so that workshop_coder.py and workshop_planner.py can read the alias from the payload.
MODEL_ALIASES: dict[str, str] = {
    "triage-specialist": "cheap-fast",
    "requirements-specialist": "cheap-fast",
    "planner-specialist": "planner-reasoner",
    "coder-specialist": "coder-worker",
    "reviewer-specialist": "reviewer-model",
}


def stage_model_alias(skill_name: str) -> str:
    """Return the LiteLLM model alias for the given specialist skill name."""
    return MODEL_ALIASES.get(skill_name, "default-worker")


def stage_policy(stage: str) -> StagePolicy:
    try:
        return STAGE_POLICIES[stage]
    except KeyError as exc:
        known_stages = ", ".join(sorted(STAGE_POLICIES))
        raise KeyError(f"no policy defined for stage {stage!r}; known stages: {known_stages}") from exc


def stage_timeout(stage: str) -> int:
    return stage_policy(stage).timeout


def stage_tool_timeout(stage: str) -> int | None:
    return stage_policy(stage).tool_timeout
