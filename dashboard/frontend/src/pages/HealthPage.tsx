import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useHealth, useModelReachability, useHealthErrors } from "@/hooks/useHealth";
import { cn } from "@/lib/utils";

function ServiceRow({ name, running, uptime }: { name: string; running: boolean; uptime?: number }) {
  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <div className="flex items-center gap-2">
        {running ? (
          <CheckCircle className="h-4 w-4 text-green-500" />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" />
        )}
        <span className="text-sm font-medium">{name}</span>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant={running ? "success" : "destructive"}>
          {running ? "Running" : "Stopped"}
        </Badge>
        {uptime != null && (
          <span className="text-xs text-muted-foreground">
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
        "inline-block h-2.5 w-2.5 rounded-full",
        status === "green" && "bg-green-500",
        status === "yellow" && "bg-amber-400",
        status === "red" && "bg-red-500",
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
                  <CardTitle className="text-sm">Services</CardTitle>
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
                  <CardTitle className="text-sm">System</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground">Disk</span>
                      <span>{diskPct}%</span>
                    </div>
                    <Progress value={diskPct} className="h-2" />
                    {healthData?.disk && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {(healthData.disk.used_bytes / 1e9).toFixed(1)} / {(healthData.disk.total_bytes / 1e9).toFixed(1)} GB
                      </p>
                    )}
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Queue depth</span>
                    <span className="font-medium">{healthData?.queue_depth ?? 0}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">HITL pending</span>
                    <span className={cn("font-medium", (healthData?.hitl_count ?? 0) > 0 && "text-amber-500")}>
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
                  <CardTitle className="text-sm">Model Alias Reachability</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {modelsData.models.map((m) => (
                      <div key={m.alias} className="flex items-center gap-2 text-sm">
                        <ReachabilityDot status={m.reachable} />
                        <span className="truncate">{m.alias}</span>
                        {m.latency_ms != null && (
                          <span className="text-xs text-muted-foreground">{m.latency_ms}ms</span>
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
                  <CardTitle className="text-sm">Recent Errors</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {errorsData.errors.slice(0, 20).map((e, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs py-1 border-b last:border-0">
                        <span className="text-muted-foreground shrink-0 tabular-nums">
                          {new Date(e.ts).toLocaleTimeString()}
                        </span>
                        <code className="text-muted-foreground shrink-0">{e.task_id.slice(0, 8)}</code>
                        <span className="text-destructive shrink-0">{e.event}</span>
                        <span className="text-muted-foreground break-all">{e.excerpt}</span>
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
