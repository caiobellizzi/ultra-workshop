import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { usePoliciesConfig, useCronJobs } from "@/hooks/useConfig";
import { config as configApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { useMutation, useQueryClient } from "@tanstack/react-query";

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
      <PageHeader title="Policies & Cron" description="Stage policies, gateway, and cron jobs" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Stage Policies</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium text-muted-foreground">Stage</th>
                      <th className="pb-2 font-medium text-muted-foreground">Timeout</th>
                      <th className="pb-2 font-medium text-muted-foreground">Auto Retries</th>
                      <th className="pb-2 font-medium text-muted-foreground">HITL on Timeout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(policies?.stage_policies ?? {}).map(([stage, policy]) => (
                      <tr key={stage} className="border-b last:border-0">
                        <td className="py-2 font-mono text-xs">{stage}</td>
                        <td className="py-2 text-xs">{policy.timeout}s</td>
                        <td className="py-2 text-xs">{policy.auto_retries}</td>
                        <td className="py-2 text-xs">{policy.hitl_on_timeout ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle className="text-sm">Hermes Service</CardTitle>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => restartMutation.mutate()}
                  disabled={restartMutation.isPending}
                >
                  {restartMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Restart"}
                </Button>
              </CardHeader>
            </Card>

            {cronData?.jobs && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Cron Jobs</CardTitle>
                </CardHeader>
                <CardContent>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 font-medium text-muted-foreground">Job</th>
                        <th className="pb-2 font-medium text-muted-foreground">Schedule</th>
                        <th className="pb-2 font-medium text-muted-foreground">Status</th>
                        <th className="pb-2 font-medium text-muted-foreground">Last Run</th>
                        <th className="pb-2 font-medium text-muted-foreground">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cronData.jobs.map((job) => (
                        <tr key={job.name} className="border-b last:border-0">
                          <td className="py-2 font-mono text-xs">{job.name}</td>
                          <td className="py-2 text-xs">{job.schedule}</td>
                          <td className="py-2 text-xs">{job.status}</td>
                          <td className="py-2 text-xs text-muted-foreground">
                            {job.last_run ? new Date(job.last_run).toLocaleString() : "Never"}
                          </td>
                          <td className="py-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() => triggerCron.mutate(job.name)}
                            >
                              Run Now
                            </Button>
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
