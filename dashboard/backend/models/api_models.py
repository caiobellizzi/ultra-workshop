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
    next_stage: str  # renamed from stage
    created_at: str
    updated_at: str
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    cost_cents_so_far: int = 0
    repo_full_name: str = ""


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]


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
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    cost_cents_so_far: int = 0
    repo_full_name: str = ""
    workspace_dir: str = ""
    default_branch: str = ""
    hitl_responses: list[Any] = Field(default_factory=list)
    recovery_decisions: list[Any] = Field(default_factory=list)
    approval_payload: Optional[dict[str, Any]] = None
    timeout_payload: Optional[dict[str, Any]] = None
    clarifications: list[Any] = Field(default_factory=list)


class ProgressResponse(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


class LaunchRequest(BaseModel):
    repo: str
    goal: str
    brainstorm: bool = False
    # Per-task overrides (Workstream B)
    branch: str = ""
    model_alias: str = ""
    skill_profile: str = "default"
    run_optional_reviewers: bool = True
    dry_run: bool = False


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


class CostSummaryResponse(BaseModel):
    today_cents: int
    daily_limit_cents: int
    this_month_cents: int
    per_task_avg_cents: int
    most_expensive_alias: str
    # Prior-period deltas (Workstream C). today vs yesterday, month vs prior month.
    today_delta_cents: int = 0
    this_month_delta_cents: int = 0


class ModelMixItem(BaseModel):
    alias: str
    count: int


class ModelMixResponse(BaseModel):
    items: list[ModelMixItem] = Field(default_factory=list)


class CostEstimateRequest(BaseModel):
    repo: str


class CostEstimateResponse(BaseModel):
    p25_cents: int
    p50_cents: int
    p75_cents: int
    sample_size: int
    basis: str  # "repo" | "global" | "none"


class QueueStatsResponse(BaseModel):
    running: int
    queued: int
    hitl_pending: int
    max_concurrency: int


class WaveBreakdownItem(BaseModel):
    role: str
    tokens_used: int
    cost_cents: int


class TaskCostRowResponse(BaseModel):
    task_id: str
    goal: str
    repo: str
    date: str
    status: str
    stage_costs: dict[str, int] = Field(default_factory=dict)
    total_cents: int
    wave_breakdown: Optional[list[WaveBreakdownItem]] = None


class TaskCostListResponse(BaseModel):
    tasks: list[TaskCostRowResponse]


class DailySpendResponse(BaseModel):
    date: str
    cents: int


class ModelSpendResponse(BaseModel):
    alias: str
    cents: int


class RoleSpendResponse(BaseModel):
    role: str
    spend_cents: int
    cap_cents: int
    month: str


class CostTrendsResponse(BaseModel):
    daily: list[DailySpendResponse]
    by_model: list[ModelSpendResponse]
    by_role: list[RoleSpendResponse]


class RoleCostListResponse(BaseModel):
    roles: list[RoleSpendResponse]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class StagePoliciesPayload(BaseModel):
    stage_policies: dict[str, dict[str, Any]]


class ModelAliasesPayload(BaseModel):
    routing: dict[str, str]  # renamed from model_aliases


class RosterPayload(BaseModel):
    reviewers: Optional[list[dict[str, Any]]] = None
    roster: Optional[list[dict[str, Any]]] = None


class CronPayload(BaseModel):
    jobs: list[dict[str, Any]]


class CronJobModel(BaseModel):
    name: str
    schedule: str
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    status: str = "disabled"
    budget_cap_cents: Optional[int] = None


class ModelAliasDef(BaseModel):
    alias: str
    provider: str
    model_id: str
    timeout: Optional[int] = None
    retries: Optional[int] = None
    fallback: Optional[str] = None


class AgentRouting(BaseModel):
    agent: str
    alias: str
    stage_timeout: Optional[int] = None


class ModelsConfigResponse(BaseModel):
    aliases: list[ModelAliasDef]
    routing: list[AgentRouting]


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

class SkillSummary(BaseModel):
    name: str
    version: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    path: str
    size: int = 0
    has_output_schema: bool = False


class SkillListResponse(BaseModel):
    skills: list[SkillSummary]


class SkillMetaModel(BaseModel):
    name: str
    version: str
    description: str
    tags: list[str]
    path: str


class SkillDetail(BaseModel):
    meta: SkillMetaModel
    content: str


class SkillUpdateRequest(BaseModel):
    content: str


class SkillRollbackRequest(BaseModel):
    commit: str = ""


class SkillDryRunRequest(BaseModel):
    content: str
    test_input: str = ""


class GitHistoryEntry(BaseModel):
    hash: str
    date: str
    message: str
    author: str


class SkillHistoryResponse(BaseModel):
    entries: list[GitHistoryEntry]


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


class HITLItem(BaseModel):
    task_id: str
    hitl_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    # Cost strip enrichment (Workstream C)
    stage: Optional[str] = None
    model: Optional[str] = None
    tokens: Optional[int] = None
    waiting_seconds: Optional[int] = None


class HITLListResponse(BaseModel):
    items: list[HITLItem]


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
    last_used: Optional[str] = None  # renamed from last_used_at
    test_command: str = ""
    # Aggregated task counts (Workstream F) — derived, not stored
    task_count: int = 0
    active_task_count: int = 0
    last_task_at: Optional[str] = None


class RepoListResponse(BaseModel):
    repos: list[RepoEntry]


class AddRepoRequest(BaseModel):
    full_name: str
    default_branch: str = "main"
    test_command: str = ""


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ServiceStatus(BaseModel):
    name: str
    running: bool
    uptime_seconds: Optional[int] = None
    version: Optional[str] = None
    # Process metrics (Workstream E) — None when not applicable (file-check services)
    pid: Optional[int] = None
    rss_bytes: Optional[int] = None
    port: Optional[int] = None


class DiskStats(BaseModel):
    used_bytes: int
    total_bytes: int
    path: str


class HealthResponse(BaseModel):
    services: list[ServiceStatus] = Field(default_factory=list)
    disk: DiskStats
    queue_depth: int = 0
    hitl_count: int = 0


class ModelReachability(BaseModel):
    alias: str
    reachable: Literal["green", "yellow", "red"]
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class ModelReachabilityResponse(BaseModel):
    models: list[ModelReachability]


class ErrorLogEntry(BaseModel):
    ts: str
    task_id: str
    event: str
    excerpt: str


class ErrorLogResponse(BaseModel):
    errors: list[ErrorLogEntry]


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
