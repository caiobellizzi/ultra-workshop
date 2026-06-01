import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { usePoliciesConfig, useCronJobs, useGlobalPolicies, useSaveGlobalPolicies } from "@/hooks/useConfig";
import { config as configApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { GlobalPolicies } from "@/types/config";

function GlobalPoliciesCard() {
  const { data, isLoading } = useGlobalPolicies();
  const save = useSaveGlobalPolicies();
  const [draft, setDraft] = useState<GlobalPolicies>({});

  useEffect(() => {
    if (data?.global_policies) setDraft(data.global_policies);
  }, [data]);

  if (isLoading) return null;

  const cost = draft.cost ?? {};
  const qh = draft.quiet_hours ?? {};
  const restart = draft.restart ?? {};

  const onSave = () =>
    save.mutate(draft, {
      onSuccess: () => toast({ title: "Global policies saved" }),
      onError: (e) => toast({ variant: "destructive", title: "Save failed", description: String(e) }),
    });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Global Policies</CardTitle>
        <Button size="sm" className="font-mono text-xs" style={{ backgroundColor: "var(--accent)", color: "var(--background)" }}
          onClick={onSave} disabled={save.isPending}>
          {save.isPending && <Loader2 className="h-3 w-3 animate-spin mr-1" />}Save
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Cost */}
        <div className="flex items-center justify-between gap-4">
          <span className="font-mono text-xs text-[--text-muted]">Task budget (seconds)</span>
          <Input
            type="number"
            className="font-mono h-8 w-32"
            value={cost.task_budget_seconds ?? ""}
            onChange={(e) => setDraft({ ...draft, cost: { ...cost, task_budget_seconds: Number(e.target.value) } })}
          />
        </div>
        {/* Quiet hours */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Checkbox id="gp-quiet" checked={qh.enabled !== false} onCheckedChange={(c) => setDraft({ ...draft, quiet_hours: { ...qh, enabled: c !== false } })} />
            <label htmlFor="gp-quiet" className="font-mono text-xs text-[--text-muted] cursor-pointer">Quiet hours</label>
          </div>
          <div className="flex items-center gap-2">
            <Input type="number" className="font-mono h-8 w-16" value={qh.start_hour ?? ""} placeholder="22"
              onChange={(e) => setDraft({ ...draft, quiet_hours: { ...qh, start_hour: Number(e.target.value) } })} />
            <span className="font-mono text-xs text-[--text-dim]">→</span>
            <Input type="number" className="font-mono h-8 w-16" value={qh.end_hour ?? ""} placeholder="7"
              onChange={(e) => setDraft({ ...draft, quiet_hours: { ...qh, end_hour: Number(e.target.value) } })} />
          </div>
        </div>
        {/* Restart */}
        <div className="flex items-center gap-2">
          <Checkbox id="gp-restart" checked={restart.allow_auto_restart === true} onCheckedChange={(c) => setDraft({ ...draft, restart: { ...restart, allow_auto_restart: c === true } })} />
          <label htmlFor="gp-restart" className="font-mono text-xs text-[--text-muted] cursor-pointer">Allow automatic restart</label>
        </div>
      </CardContent>
    </Card>
  );
}
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";

export function PoliciesConfigPage() {
  const { data: policies, isLoading } = usePoliciesConfig();
  const { data: cronData } = useCronJobs();
  const qc = useQueryClient();

  const restartMutation = useMutation({
    mutationFn: () => configApi.restartHermes(),
    onSuccess: () => toast({ title: "Restart triggered" }),
    onError: (e) => toast({ variant: "destructive", title: "Failed", description: String(e) }),
  });

  const triggerCron = useMutation({
    mutationFn: (name: string) => configApi.triggerCronJob(name),
    onSuccess: () => {
      toast({ title: "Job triggered" });
      void qc.invalidateQueries({ queryKey: ["cron"] });
    },
  });

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Policies" description="Controls agent behavior, cost limits, and cron. Changes apply to all new tasks." />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-[--text-muted]" />
          </div>
        ) : (
          <>
            <GlobalPoliciesCard />

            <Card>
              <CardHeader>
                <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Stage Policies</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full">
                  <thead className="bg-[--surface]">
                    <tr className="border-b border-[--border] text-left">
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Stage</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Timeout</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Auto Retries</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">HITL on Timeout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(policies?.stage_policies ?? {}).map(([stage, policy]) => (
                      <tr key={stage} className="border-b border-[--border] last:border-0">
                        <td className="py-2 font-mono text-xs text-[--text-m]">{stage}</td>
                        <td className="py-2 font-mono text-xs text-[--text-m]">{policy.timeout}s</td>
                        <td className="py-2 font-mono text-xs text-[--text-m]">{policy.auto_retries}</td>
                        <td className="py-2">
                          {policy.hitl_on_timeout ? (
                            <span className="font-mono text-xs text-[--success] bg-[--success-bg] border border-[--success-border] px-1.5 py-0.5 rounded-[--radius-sm]">ON</span>
                          ) : (
                            <span className="font-mono text-xs text-[--text-muted] bg-[--surface-raised] px-1.5 py-0.5 rounded-[--radius-sm]">OFF</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-start justify-between gap-4">
                <div>
                  <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Hermes Service</CardTitle>
                  <p className="font-mono text-xs text-[--text-dim] mt-1 max-w-md" style={{ lineHeight: 1.5 }}>
                    <span style={{ color: "var(--warning)" }}>⚠ </span>
                    Restarting interrupts in-flight tasks and briefly stalls the queue. Use only when the dispatcher is wedged.
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <button
                      disabled={restartMutation.isPending}
                      className="border border-[--danger-border] text-[--danger] bg-[--surface] font-mono text-xs px-3 py-1 rounded-[--radius-sm] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 hover:border-[--danger] transition-colors"
                    >
                      {restartMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                      Restart Hermes
                    </button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Restart Hermes?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will restart the Hermes gateway service. In-flight tasks may be interrupted.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => restartMutation.mutate()}>
                        Restart
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </CardHeader>
            </Card>

            {cronData?.jobs && (
              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Cron Jobs</CardTitle>
                </CardHeader>
                <CardContent>
                  <table className="w-full">
                    <thead className="bg-[--surface]">
                      <tr className="border-b border-[--border] text-left">
                        <th className="py-2 font-mono text-xs text-[--text-muted]">Job</th>
                        <th className="py-2 font-mono text-xs text-[--text-muted]">Schedule</th>
                        <th className="py-2 font-mono text-xs text-[--text-muted]">Status</th>
                        <th className="py-2 font-mono text-xs text-[--text-muted]">Last Run</th>
                        <th className="py-2 font-mono text-xs text-[--text-muted]">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cronData.jobs.map((job) => (
                        <tr key={job.name} className="border-b border-[--border] last:border-0">
                          <td className="py-2 font-mono text-xs text-[--text-m]">{job.name}</td>
                          <td className="py-2 font-mono text-xs text-[--info]">{job.schedule}</td>
                          <td className="py-2 font-mono text-xs text-[--text-m]">{job.status}</td>
                          <td className="py-2 font-mono text-xs text-[--text-muted]">
                            {job.last_run ? new Date(job.last_run).toLocaleString() : "Never"}
                          </td>
                          <td className="py-2">
                            <button
                              onClick={() => triggerCron.mutate(job.name)}
                              className="border border-[--border-strong] text-[--text-m] font-mono text-xs px-2 py-0.5 rounded-[--radius-sm] hover:border-[--border-strong] transition-colors"
                            >
                              Run Now
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}
