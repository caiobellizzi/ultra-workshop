import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePoliciesConfig, useCronJobs } from "@/hooks/useConfig";
import { config as configApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
