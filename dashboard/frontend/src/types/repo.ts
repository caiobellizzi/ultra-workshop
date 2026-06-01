export interface Repo {
  full_name: string;
  default_branch: string;
  active: boolean;
  last_used: string | null;
  task_count?: number;
  active_task_count?: number;
  last_task_at?: string | null;
}

export interface HITLItem {
  task_id: string;
  hitl_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  stage?: string | null;
  model?: string | null;
  tokens?: number | null;
  waiting_seconds?: number | null;
}
