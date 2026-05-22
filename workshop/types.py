# Deploy location: /opt/ultra-workshop/workshop/types.py
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str
    description: str
    files: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]
    affected_files: list[str] = Field(default_factory=list)


class FileChange(BaseModel):
    path: str
    diff: str


class Diff(BaseModel):
    summary: str
    changes: list[FileChange]
    branch: str           # workshop/<id>-<slug>
    workspace_dir: str    # /tmp/uws-sandbox-<task-id>/ — coder sets this, pr_opener uses for git push


class Review(BaseModel):
    passed: bool
    feedback: str
    blocking_issues: list[str] = Field(default_factory=list)


class Issue(BaseModel):
    url: str
    title: str
    body: str
    number: int


class IngestResult(BaseModel):
    run_id: str
    status: str
    adr_path: str
