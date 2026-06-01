export interface SkillMeta {
  name: string;
  version: string;
  description: string;
  tags: string[];
  path: string;
  enabled?: boolean;
  size?: number;
  has_output_schema?: boolean;
}

export interface SkillDetail {
  meta: SkillMeta;
  content: string;
  config_yml?: string | null;
  hooks_yml?: string | null;
}

export interface SkillStat {
  agent: string;
  runs_today: number;
  avg_duration_seconds?: number | null;
  last_run?: string | null;
}

export interface ReviewerStat {
  role: string;
  reviews_run: number;
  issues_found: number;
  avg_latency_seconds?: number | null;
  last_run?: string | null;
}

export interface GitHistoryEntry {
  hash: string;
  date: string;
  message: string;
  author: string;
}
