from __future__ import annotations

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
    "planner": StagePolicy(timeout=300, auto_retries=1),
    "coder": StagePolicy(timeout=960, tool_timeout=900, auto_retries=0, hitl_on_timeout=True),
    "reviewer": StagePolicy(timeout=300, auto_retries=1),
}


def stage_policy(stage: str) -> StagePolicy:
    return STAGE_POLICIES[stage]


def stage_timeout(stage: str) -> int:
    return stage_policy(stage).timeout


def stage_tool_timeout(stage: str) -> int | None:
    return stage_policy(stage).tool_timeout
