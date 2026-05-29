export interface ServiceStatus {
  name: string;
  running: boolean;
  uptime_seconds?: number;
  version?: string;
}

export interface DiskStats {
  used_bytes: number;
  total_bytes: number;
  path: string;
}

export interface HealthResponse {
  services: ServiceStatus[];
  disk: DiskStats;
  queue_depth: number;
  hitl_count: number;
}

export interface ModelReachability {
  alias: string;
  reachable: "green" | "yellow" | "red";
  latency_ms?: number;
  error?: string;
}

export interface ErrorLogEntry {
  ts: string;
  task_id: string;
  event: string;
  excerpt: string;
}
