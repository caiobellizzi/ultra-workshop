# Deploy location: /opt/ultra-workshop/workshop/types.py
from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator


class PlanStep(BaseModel):
    id: str
    description: str
    files: list[str] = Field(default_factory=list)
    model_alias: str = "coder-worker"


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]
    affected_files: list[str] = Field(default_factory=list)


class FileChange(BaseModel):
    model_config = {"populate_by_name": True}

    path: str = Field(validation_alias=AliasChoices("path", "file"))
    diff: str


class Diff(BaseModel):
    summary: str
    changes: list[FileChange]
    branch: str           # workshop/<id>-<slug>
    workspace_dir: str    # /tmp/uws-sandbox-<task-id>/ — coder sets this, pr_opener uses for git push
    build_passed: bool = True
    test_passed: bool = True
    output_tail: str = ""


class ReviewIssue(BaseModel):
    file: str = "*"
    problem: str
    required_fix: str

    def __str__(self) -> str:
        return f"{self.file}: {self.problem} Required fix: {self.required_fix}"

    def __contains__(self, needle: str) -> bool:
        return needle in str(self)


class Review(BaseModel):
    passed: bool
    feedback: str
    blocking_issues: list[ReviewIssue] = Field(default_factory=list)

    @field_validator("blocking_issues", mode="before")
    @classmethod
    def _normalize_blocking_issues(cls, value):
        if not value:
            return []
        normalized = []
        for item in value:
            if isinstance(item, str):
                normalized.append(
                    {
                        "file": "*",
                        "problem": item,
                        "required_fix": "Fix the reported blocking issue and retry.",
                    }
                )
            else:
                normalized.append(item)
        return normalized


class ClarificationQuestion(BaseModel):
    question: str
    options: list[str] = Field(default_factory=list)
    context: str = ""


class ClarificationRequest(BaseModel):
    needs_clarification: Literal[True] = True
    task_id: str
    source_stage: str
    reason: str
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    allow_free_text: bool = True
    evidence: list[str] = Field(default_factory=list)
    summary: str = ""


class Issue(BaseModel):
    url: str
    title: str
    body: str
    number: int


class IngestResult(BaseModel):
    run_id: str
    status: str
    adr_path: str


class ReviewFinding(BaseModel):
    file: str
    line: int | None = None
    problem: str
    required_fix: str
    severity: Literal["Critical", "Important", "Minor"]

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError(f"severity must be a string, got {type(value)}")
        upper = value.upper()
        if upper in ("CRITICAL", "HIGH"):
            return "Critical"
        if upper in ("IMPORTANT", "MEDIUM"):
            return "Important"
        if upper in ("MINOR", "LOW"):
            return "Minor"
        raise ValueError(
            f"unrecognized severity {value!r}; expected Critical/High, Important/Medium, or Minor/Low"
        )


class WaveReport(BaseModel):
    role: str
    passed: bool
    findings: list[ReviewFinding] = Field(default_factory=list)
    tokens_used: int = 0
    cost_cents: float = 0.0


class MergeReport(BaseModel):
    block_push: bool
    critical_findings: list[ReviewFinding] = Field(default_factory=list)
    important_findings: list[ReviewFinding] = Field(default_factory=list)
    auto_fixed: list[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
