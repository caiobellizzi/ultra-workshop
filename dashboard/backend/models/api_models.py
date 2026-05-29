"""Pydantic request/response models for the dashboard REST API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    ok: bool
    detail: str = ""


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskSummary(BaseModel):
    task_id: str
    status: str
    goal: str
    repo: str
    stage: str  # next_stage
    created_at: str
    updated_at: str


class TaskDetail(BaseModel):
    task_id: str
    status: str
    goal: str
    repo: str
    next_stage: str
    created_at: str
    updated_at: str
    stages: dict[str, Any] = Field(default_factory=dict)
    attempts: dict[str, Any] = Field(default_factory=dict)
    current_step: int = 0
    approval_payload: dict[str, Any] = Field(default_factory=dict)
    timeout_payload: dict[str, Any] = Field(default_factory=dict)
    clarifications: list[Any] = Field(default_factory=list)


class LaunchRequest(BaseModel):
    repo: str
    goal: str
    brainstorm: bool = False


class LaunchResponse(BaseModel):
    task_id: str


class FixRequest(BaseModel):
    task_id: str


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------

class DailyCost(BaseModel):
    date: str
    total_usd: float


class RoleCost(BaseModel):
    role: str
    monthly_cents: float
    cap_cents: int
    pct: float


class TaskCost(BaseModel):
    task_id: str
    total_usd: float
    breakdown: list[dict[str, Any]] = Field(default_factory=list)


class ModelCost(BaseModel):
    model: str
    total_usd: float
    request_count: int


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class StagePoliciesPayload(BaseModel):
    stage_policies: dict[str, dict[str, Any]]


class ModelAliasesPayload(BaseModel):
    model_aliases: dict[str, str]


class RosterPayload(BaseModel):
    reviewers: list[dict[str, Any]]


class CronPayload(BaseModel):
    jobs: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

class SkillSummary(BaseModel):
    name: str
    path: str
    size: int
    has_output_schema: bool


class SkillDetail(BaseModel):
    name: str
    content: str
    path: str
    size: int
    has_output_schema: bool


class SkillUpdateRequest(BaseModel):
    content: str


class SkillRollbackRequest(BaseModel):
    # rollback to .bak file
    pass


class SkillDryRunRequest(BaseModel):
    content: str
    test_input: str = ""


# ---------------------------------------------------------------------------
# HITL
# ---------------------------------------------------------------------------

class HitlRow(BaseModel):
    id: int
    session_id: str
    message_id: Optional[str] = None
    task_description: str
    created_at: str
    status: str
    telegram_chat_id: str
    telegram_message_id: Optional[str] = None


class HitlResolveRequest(BaseModel):
    task_id: str
    hitl_type: str
    choice: str


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------

class RepoEntry(BaseModel):
    full_name: str
    active: bool = True
    default_branch: str = "main"
    visibility: str = "unknown"
    viewer_permission: str = "UNKNOWN"
    source: str = "manual"
    created_at: str = ""
    updated_at: str = ""
    last_used_at: Optional[str] = None
    test_command: str = ""


class AddRepoRequest(BaseModel):
    full_name: str
    default_branch: str = "main"
    test_command: str = ""


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ServiceStatus(BaseModel):
    name: str
    ok: bool
    detail: str = ""


class HealthResponse(BaseModel):
    ok: bool
    services: list[ServiceStatus] = Field(default_factory=list)
    queue_depth: int = 0
    disk_free_gb: float = 0.0


# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------

class RestartRequest(BaseModel):
    force: bool = False


class RestartResponse(BaseModel):
    ok: bool
    detail: str = ""


# ---------------------------------------------------------------------------
# Internal (spend-update — receives LiteLLM SPEND_LOGS_URL batches)
# ---------------------------------------------------------------------------

class SpendLogEntry(BaseModel):
    """Single spend log entry from LiteLLM SPEND_LOGS_URL callback."""
    model_config = {"extra": "allow"}

    request_id: Optional[str] = None
    call_type: Optional[str] = None
    model: Optional[str] = None
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    response_cost: Optional[float] = None
    user: Optional[str] = None  # aider --user <task_id>
    metadata: Optional[dict[str, Any]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class SpendUpdatePayload(BaseModel):
    """Batch payload from LiteLLM SPEND_LOGS_URL."""
    model_config = {"extra": "allow"}

    # LiteLLM may send a list directly or wrap in a dict
    logs: Optional[list[SpendLogEntry]] = None
