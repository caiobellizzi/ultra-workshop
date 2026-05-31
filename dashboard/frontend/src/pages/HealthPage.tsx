import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useHealth, useModelReachability, useHealthErrors } from "@/hooks/useHealth";
import { cn } from "@/lib/utils";

function ServiceRow({ name, running, uptime }: { name: string; running: boolean; uptime?: number }) {
  return (
    <div className="flex items-center justify-between border-b border-[--border] py-2 last:border-0">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-block h-2 w-2 rounded-full",
            running ? "bg-[--success]" : "bg-[--danger]",
          )}
        />
        <span className="font-mono text-[--text-base] text-[--text]">{name}</span>
      </div>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "font-mono text-xs border px-1.5 py-0.5 rounded-[--radius-sm]",
            running
              ? "text-[--success] bg-[--success-bg] border-[--success-border]"
              : "text-[--danger] bg-[--danger-bg] border-[--danger-border]",
          )}
        >
          {running ? "✓ running" : "✗ stopped"}
        </span>
        {uptime != null && (
          <span className="font-mono text-xs text-[--text-muted]">
            {Math.floor(uptime / 3600)}h uptime
          </span>
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
      <PageHeader title="Health" description="System status" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Services */}
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="font-mono text-xs tracking-widest uppercase text-[--text-dim]">Services</CardTitle>
                </CardHeader>
                <CardContent>
                  {healthData?.services.map((s) => (
                    <ServiceRow key={s.name} name={s.name} running={s.running} uptime={s.uptime_seconds} />
                  ))}
                </CardContent>
              </Card>

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
