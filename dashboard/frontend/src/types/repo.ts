export interface Repo {
  full_name: string;
  default_branch: string;
  active: boolean;
  last_used: string | null;
}

export interface HITLItem {
  task_id: string;
  hitl_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}
