import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useHealth, useModelReachability, useHealthErrors } from "@/hooks/useHealth";
import { cn } from "@/lib/utils";

function formatUptime(secs?: number): string {
  if (secs == null) return "—";
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return `${d}d ${h}h ${m}m`;
}

function fmtBytes(b?: number | null): string {
  if (b == null) return "—";
  if (b >= 1e9) return `${(b / 1e9).toFixed(2)} GB`;
  if (b >= 1e6) return `${(b / 1e6).toFixed(1)} MB`;
  if (b >= 1e3) return `${(b / 1e3).toFixed(0)} KB`;
  return `${b} B`;
}

function ServiceCard({ name, running, uptime, version, pid, rss, port }: { name: string; running: boolean; uptime?: number; version?: string; pid?: number | null; rss?: number | null; port?: number | null }) {
  return (
    <div
      className="rounded-sm p-3"
      style={{
        backgroundColor: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `2px solid ${running ? "var(--success)" : "var(--danger)"}`,
      }}
    >
      <div className="flex items-center justify-between mb-2.5">
        <span className="font-mono" style={{ fontSize: "var(--text-sm)", color: "var(--text)" }}>{name}</span>
        <span className={cn("inline-block h-2 w-2 rounded-full", running ? "bg-[--success]" : "bg-[--danger]")} />
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between">
          <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>status</span>
          <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: running ? "var(--success)" : "var(--danger)" }}>
            {running ? "running" : "stopped"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>uptime</span>
          <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{formatUptime(uptime)}</span>
        </div>
        {version && (
          <div className="flex justify-between">
            <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>version</span>
            <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{version}</span>
          </div>
        )}
        {(pid != null || rss != null || port != null) && (
          <>
            <div className="flex justify-between">
              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>pid</span>
              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{pid ?? "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>memory</span>
              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{fmtBytes(rss)}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>port</span>
              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{port ?? "—"}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ReachabilityDot({ status }: { status: "green" | "yellow" | "red" }) {
  return (
    <span
      className={cn(
        "inline-block h-2 w-2 rounded-full",
        status === "green" && "bg-[--success]",
        status === "yellow" && "bg-[--warning]",
        status === "red" && "bg-[--danger]",
      )}
    />
  );
}

export function HealthPage() {
  const { data: healthData, isLoading } = useHealth();
  const { data: modelsData } = useModelReachability();
  const { data: errorsData } = useHealthErrors();

  const diskPct = healthData?.disk
    ? Math.round((healthData.disk.used_bytes / healthData.disk.total_bytes) * 100)
    : 0;

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="System Health" description="Service status and system metrics" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Service cards */}
            <div>
              <p className="font-mono uppercase mb-3" style={{ fontSize: "var(--text-xs)", letterSpacing: "var(--tracking-wide)", color: "var(--text-dim)" }}>Services</p>
              <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}>
                {healthData?.services.map((s) => (
                  <ServiceCard key={s.name} name={s.name} running={s.running} uptime={s.uptime_seconds} version={s.version} pid={s.pid} rss={s.rss_bytes} port={s.port} />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-xs tracking-widest uppercase text-[--text-dim]">System</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between font-mono text-xs mb-1">
                      <span className="text-[--text-muted]">Disk</span>
                      <span className="text-[--text]">{diskPct}%</span>
                    </div>
                    <Progress value={diskPct} className="h-1.5 bg-[--surface-raised] [&>div]:bg-[--success]" />
                    {healthData?.disk && (
                      <p className="font-mono text-xs text-[--text-muted] mt-1">
                        {(healthData.disk.used_bytes / 1e9).toFixed(1)} / {(healthData.disk.total_bytes / 1e9).toFixed(1)} GB
                      </p>
                    )}
                  </div>
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-[--text-muted]">Queue depth</span>
                    <span className="text-[--text]">{healthData?.queue_depth ?? 0}</span>
                  </div>
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-[--text-muted]">HITL pending</span>
                    <span className={cn("text-[--text]", (healthData?.hitl_count ?? 0) > 0 && "text-[--warning]")}>
                      {healthData?.hitl_count ?? 0}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Model reachability */}
            {modelsData?.models && (
              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-xs tracking-widest uppercase text-[--text-dim]">Model Alias Reachability</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {modelsData.models.map((m) => (
                      <div key={m.alias} className="flex items-center gap-2 font-mono text-xs">
                        <ReachabilityDot status={m.reachable} />
                        <span className="truncate text-[--text]">{m.alias}</span>
                        {m.latency_ms != null && (
                          <span className="text-[--text-muted]">{m.latency_ms}ms</span>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Recent errors */}
            {errorsData?.errors && errorsData.errors.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-xs tracking-widest uppercase text-[--text-dim]">Recent Errors</CardTitle>
                </CardHeader>
                <CardContent>
                  <div>
                    {errorsData.errors.slice(0, 20).map((e, i) => (
                      <div key={i} className="flex items-start gap-2 font-mono text-xs border-b border-[--border] py-2 last:border-0">
                        <span className="text-[--text-muted] shrink-0 tabular-nums">
                          {new Date(e.ts).toLocaleTimeString()}
                        </span>
                        <span className="text-[--text-muted] shrink-0">{e.task_id.slice(0, 8)}</span>
                        <span className="text-[--danger] shrink-0">{e.event}</span>
                        <span className="text-[--text-muted] break-all">{e.excerpt}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}
