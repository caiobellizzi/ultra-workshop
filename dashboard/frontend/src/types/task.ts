// Mirrors workshop/types.py and state.json schema

export type TaskStatus =
  | "running"
  | "needs_approval"
  | "needs_clarification"
  | "needs_step_recovery"
  | "needs_review_recovery"
  | "needs_timeout_recovery"
  | "stopped"
  | "approval_rejected"
  | "pushing"
  | "pushed"
  | "push_failed";

export type PipelineStage =
  | "brainstorm"
  | "triage"
  | "requirements"
  | "planner"
  | "coder"
  | "reviewer"
  | "approval";

export const STAGE_ORDER: PipelineStage[] = [
  "brainstorm",
  "triage",
  "requirements",
  "planner",
  "coder",
  "reviewer",
  "approval",
];

// --- Plan types ---
export interface PlanStep {
  id: string;
  description: string;
  files: string[];
  model_alias?: string;
}

export interface Plan {
  goal: string;
  steps: PlanStep[];
  affected_files: string[];
}

// --- Diff types ---
export interface FileChange {
  path: string;
  diff: string;
  additions: number;
  deletions: number;
}

export interface Diff {
  summary: string;
  changes: FileChange[];
  branch: string;
  build_passed: boolean;
  test_passed: boolean;
  output_tail: string;
}

// --- Review types ---
export type FindingSeverity = "Critical" | "Important" | "Minor";

export interface ReviewFinding {
  file: string;
  line: number | null;
  problem: string;
  required_fix: string;
  severity: FindingSeverity;
}

export interface WaveReport {
  role: string;
  passed: boolean;
  findings: ReviewFinding[];
  tokens_used: number;
  cost_cents: number;
}

export interface MergeReport {
  block_push: boolean;
  critical_findings: ReviewFinding[];
  important_findings: ReviewFinding[];
  auto_fixed: string[];
  summary: string;
}

// --- Clarification types ---
export interface ClarificationRequest {
  task_id: string;
  source_stage: string;
  reason: string;
  questions: string[];
  options: string[][];
  allow_free_text: boolean;
  evidence: string[];
}

// --- HITL payload types ---
export type HITLType =
  | "approval"
  | "clarification"
  | "step_retry_exhausted"
  | "review_retry_exhausted"
  | "timeout_recovery"
  | "brainstorm";

export interface ApprovalPayload {
  hitl_type: "approval";
  plan: Plan;
  options: string[];
}

export interface ClarificationPayload {
  hitl_type: "clarification";
  request: ClarificationRequest;
}

export interface StepRetryPayload {
  hitl_type: "step_retry_exhausted";
  step_idx: number;
  step_desc: string;
  decompose_attempted: boolean;
  reason: string;
  options: string[];
}

export interface ReviewRetryPayload {
  hitl_type: "review_retry_exhausted";
  blocking_issues: ReviewFinding[];
  branch: string;
  diff_summary: string;
  options: string[];
}

export interface TimeoutRecoveryPayload {
  hitl_type: "timeout_recovery";
  stage: string;
  attempt: number;
  reason: string;
  options: string[];
}

export interface BrainstormPayload {
  hitl_type: "brainstorm";
  approved: boolean;
  goal_statement: string;
  follow_up: string | null;
}

export type HITLPayload =
  | ApprovalPayload
  | ClarificationPayload
  | StepRetryPayload
  | ReviewRetryPayload
  | TimeoutRecoveryPayload
  | BrainstormPayload;

// --- Stage result shapes ---
export interface TriageResult {
  task_type: string;
  complexity: string;
  summary: string;
}

export interface RequirementsResult {
  ready: boolean;
  context: string;
}

// --- Task state types ---
export interface StageData {
  result?: unknown;
  attempts: number;
}

export interface TaskStages {
  triage?: TriageResult;
  requirements?: RequirementsResult;
  planner?: Plan;
  diff?: Diff;
  wave_reports?: WaveReport[];
  merge_report?: MergeReport;
}

export interface TaskSummary {
  task_id: string;
  goal: string;
  repo: string;
  status: TaskStatus;
  next_stage: PipelineStage;
  current_step: number | null;
  total_steps: number | null;
  created_at: string;
  updated_at: string;
  cost_cents_so_far: number;
  repo_full_name: string;
}

export interface TaskDetail extends TaskSummary {
  workspace_dir: string;
  default_branch: string;
  attempts: Record<string, number>;
  clarifications: ClarificationRequest[];
  hitl_responses: unknown[];
  recovery_decisions: unknown[];
  approval_payload: HITLPayload | null;
  timeout_payload: TimeoutRecoveryPayload | null;
  stages: TaskStages;
}

// --- Progress log events ---
export type ProgressEventType =
  | "triage_complete"
  | "requirements_complete"
  | "plan_complete"
  | "coder_complete"
  | "clarification_requested"
  | "clarification_received"
  | "stage_retry"
  | "step_retry_exhausted"
  | "timeout_recovery_requested"
  | "wave_complete"
  | "merge_complete";

export interface ProgressEvent {
  ts: string;
  event: ProgressEventType;
  [key: string]: unknown;
}

export type StageNodeStatus =
  | "pending"
  | "running"
  | "success"
  | "failed_retry"
  | "failed"
  | "paused_hitl"
  | "skipped";
