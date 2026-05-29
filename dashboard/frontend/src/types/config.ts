// Config types mirroring hermes-config YAML structures

export interface StagePolicy {
  timeout: number;
  tool_timeout?: number;
  auto_retries: number;
  hitl_on_timeout?: boolean;
}

export type StageName =
  | "brainstorm"
  | "triage"
  | "requirements"
  | "planner"
  | "coder"
  | "reviewer";

export interface StagePoliciesConfig {
  stage_policies: Record<StageName, StagePolicy>;
  model_aliases: Record<string, string>;
}

// LiteLLM alias definition
export interface ModelAlias {
  alias: string;
  provider: string;
  model_id: string;
  timeout?: number;
  retries?: number;
  fallback?: string[];
  reachable?: "green" | "yellow" | "red";
  last_latency_ms?: number;
}

// Agent routing (agent name → alias)
export interface AgentRouting {
  agent: string;
  alias: string;
  stage_timeout?: number;
}

export interface ModelsConfig {
  aliases: ModelAlias[];
  routing: AgentRouting[];
}

// Reviewer roster
export interface ReviewerEntry {
  role: string;
  model_alias: string;
  isolation: boolean;
  file_patterns: string[];
  monthly_budget_cents?: number;
  fallback_alias?: string;
  mtd_spend_cents?: number;
  budget_pct?: number;
}

// Cron job
export interface CronJob {
  name: string;
  schedule: string;
  last_run: string | null;
  next_run: string | null;
  status: "enabled" | "disabled" | "running";
  budget_cap_cents?: number;
}

// Config policies response
export interface PoliciesConfig {
  stage_policies: Record<StageName, StagePolicy>;
}
