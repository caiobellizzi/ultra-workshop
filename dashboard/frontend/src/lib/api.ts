// Typed API client for the UWS Dashboard backend.
// All paths are relative so the Vite dev proxy routes them to :7010.
import type { TaskSummary, TaskDetail, ProgressEvent } from "@/types/task";
import type {
  ModelsConfig,
  ReviewerEntry,
  PoliciesConfig,
  CronJob,
} from "@/types/config";
import type {
  CostSummary,
  TaskCostRow,
  CostTrends,
  RoleSpend,
} from "@/types/cost";
import type {
  HealthResponse,
  ModelReachability,
  ErrorLogEntry,
} from "@/types/health";
import type { SkillMeta, SkillDetail, GitHistoryEntry } from "@/types/skill";
import type { Repo, HITLItem } from "@/types/repo";

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  // Backend routes are all under /api. Some call sites omit the prefix and
  // relied on a Vite dev proxy; in the production build (served by the backend
  // itself, no proxy) we must normalize to the /api base.
  const url = path.startsWith("/api/") ? path : `/api${path}`;
  const res = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    },
    ...init,
  });
  if (res.status === 401) {
    // Let the auth layer handle redirect
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  login: (password: string) =>
    request<{ ok: boolean }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<{ authenticated: boolean }>("/auth/me"),
};

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export const tasks = {
  list: (params?: { status?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    return request<{ tasks: TaskSummary[] }>(`/api/tasks?${qs}`);
  },
  get: (id: string) => request<TaskDetail>(`/api/tasks/${id}`),
  progress: (id: string) =>
    request<{ events: ProgressEvent[] }>(`/api/tasks/${id}/progress`),
  create: (body: { repo: string; goal: string; brainstorm?: boolean }) =>
    request<{ task_id: string }>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  fix: (id: string) =>
    request<{ ok: boolean }>(`/api/tasks/${id}/fix`, { method: "POST" }),
  resolveHitl: (
    id: string,
    body: { decision: string; free_text?: string },
  ) =>
    request<{ ok: boolean }>(`/api/tasks/${id}/hitl`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ---------------------------------------------------------------------------
// HITL queue
// ---------------------------------------------------------------------------

export const hitl = {
  list: () => request<{ items: HITLItem[] }>("/api/hitl"),
};

// ---------------------------------------------------------------------------
// Cost
// ---------------------------------------------------------------------------

export const cost = {
  summary: (params?: { from?: string; to?: string }) => {
    const qs = new URLSearchParams(
      params as Record<string, string> | undefined,
    );
    return request<CostSummary>(`/api/cost/summary?${qs}`);
  },
  tasks: (params?: { from?: string; to?: string }) => {
    const qs = new URLSearchParams(
      params as Record<string, string> | undefined,
    );
    return request<{ tasks: TaskCostRow[] }>(`/api/cost/tasks?${qs}`);
  },
  trends: (params?: { from?: string; to?: string }) => {
    const qs = new URLSearchParams(
      params as Record<string, string> | undefined,
    );
    return request<CostTrends>(`/api/cost/trends?${qs}`);
  },
  roles: () => request<{ roles: RoleSpend[] }>("/api/cost/roles"),
  task: (id: string) => request<TaskCostRow>(`/api/cost/task/${id}`),
};

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

export const config = {
  getModels: () => request<ModelsConfig>("/api/config/models"),
  putModelAliases: (routing: Record<string, string>) =>
    request<{ ok: boolean }>("/api/config/models/aliases", {
      method: "PUT",
      body: JSON.stringify({ routing }),
    }),
  getReviewers: () =>
    request<{ reviewers: ReviewerEntry[] }>("/api/config/reviewers"),
  putReviewers: (reviewers: ReviewerEntry[]) =>
    request<{ ok: boolean }>("/api/config/reviewers", {
      method: "PUT",
      body: JSON.stringify({ reviewers }),
    }),
  getPolicies: () => request<PoliciesConfig>("/api/config/stage-policies"),
  putPolicies: (policies: PoliciesConfig) =>
    request<{ ok: boolean }>("/api/config/stage-policies", {
      method: "PUT",
      body: JSON.stringify(policies),
    }),
  getRoster: () =>
    request<{ roster: ReviewerEntry[] }>("/api/config/roster"),
  putRoster: (roster: ReviewerEntry[]) =>
    request<{ ok: boolean }>("/api/config/roster", {
      method: "PUT",
      body: JSON.stringify({ roster }),
    }),
  getCron: () => request<{ jobs: CronJob[] }>("/api/cron"),
  putCronJob: (name: string, data: Partial<CronJob>) =>
    request<{ ok: boolean }>(`/api/cron/${name}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  triggerCronJob: (name: string) =>
    request<{ ok: boolean }>(`/api/cron/${name}/trigger`, {
      method: "POST",
    }),
  reloadLitellm: () =>
    request<{ ok: boolean }>("/api/control/reload-litellm", {
      method: "POST",
    }),
  restartHermes: () =>
    request<{ ok: boolean }>("/api/control/restart", { method: "POST" }),
};

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export const skills = {
  list: () => request<{ skills: SkillMeta[] }>("/api/skills"),
  get: (name: string) => request<SkillDetail>(`/api/skills/${name}`),
  put: (name: string, content: string) =>
    request<{ ok: boolean }>(`/api/skills/${name}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  history: (name: string) =>
    request<{ entries: GitHistoryEntry[] }>(`/api/skills/${name}/history`),
  rollback: (name: string, commit: string) =>
    request<{ ok: boolean }>(`/api/skills/${name}/rollback`, {
      method: "POST",
      body: JSON.stringify({ commit }),
    }),
};

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export const health = {
  get: () => request<HealthResponse>("/api/health"),
  models: () =>
    request<{ models: ModelReachability[] }>("/api/health/models"),
  errors: () =>
    request<{ errors: ErrorLogEntry[] }>("/api/health/errors"),
};

// ---------------------------------------------------------------------------
// Repos
// ---------------------------------------------------------------------------

export const repos = {
  list: () => request<{ repos: Repo[] }>("/api/repos"),
  add: (repo: string) =>
    request<{ ok: boolean }>("/api/repos", {
      method: "POST",
      body: JSON.stringify({ repo }),
    }),
  update: (fullName: string, data: Partial<Repo>) =>
    request<{ ok: boolean }>(`/api/repos/${encodeURIComponent(fullName)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  remove: (fullName: string) =>
    request<void>(`/api/repos/${encodeURIComponent(fullName)}`, {
      method: "DELETE",
    }),
};

// ---------------------------------------------------------------------------
// Launch
// ---------------------------------------------------------------------------

export const launch = {
  build: (body: { repo: string; goal: string; brainstorm?: boolean }) =>
    request<{ task_id: string }>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  fix: (body: { task_id: string; instructions?: string }) =>
    request<{ task_id: string }>(`/api/tasks/${body.task_id}/fix`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export { ApiError };
