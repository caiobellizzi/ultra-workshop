export interface CostSummary {
  today_cents: number;
  daily_limit_cents: number;
  this_month_cents: number;
  per_task_avg_cents: number;
  most_expensive_alias: string;
  today_delta_cents?: number;
  this_month_delta_cents?: number;
}

export interface ModelMixItem {
  alias: string;
  count: number;
}

export interface CostEstimate {
  p25_cents: number;
  p50_cents: number;
  p75_cents: number;
  sample_size: number;
  basis: "repo" | "global" | "none";
}

export interface TaskCostRow {
  task_id: string;
  goal: string;
  repo: string;
  date: string;
  status: string;
  stage_costs: Record<string, number>;
  total_cents: number;
  wave_breakdown?: Array<{ role: string; tokens_used: number; cost_cents: number }>;
}

export interface DailySpend {
  date: string;
  cents: number;
}

export interface ModelSpend {
  alias: string;
  cents: number;
}

export interface RoleSpend {
  role: string;
  spend_cents: number;
  cap_cents: number;
  month: string;
}

export interface CostTrends {
  daily: DailySpend[];
  by_model: ModelSpend[];
  by_role: RoleSpend[];
}
