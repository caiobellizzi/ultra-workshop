export interface SkillMeta {
  name: string;
  version: string;
  description: string;
  tags: string[];
  path: string;
}

export interface SkillDetail {
  meta: SkillMeta;
  content: string;
}

export interface GitHistoryEntry {
  hash: string;
  date: string;
  message: string;
  author: string;
}
