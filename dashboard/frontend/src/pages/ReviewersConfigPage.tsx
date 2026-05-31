import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useReviewersConfig } from "@/hooks/useConfig";
import { useCostRoles } from "@/hooks/useCost";
import { formatCents } from "@/lib/utils";

export function ReviewersConfigPage() {
  const { data, isLoading } = useReviewersConfig();
  const { data: rolesData } = useCostRoles();

  const roleSpend = Object.fromEntries(
    (rolesData?.roles ?? []).map((r) => [r.role, r])
  );

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Reviewer Config" description="Review roster and model assignments" />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-[--text-muted]" />
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Reviewer Roster</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead className="bg-[--surface]">
                  <tr className="border-b border-[--border] text-left">
                    <th className="py-2 font-mono text-xs text-[--text-muted]">Role</th>
                    <th className="py-2 font-mono text-xs text-[--text-muted]">Model Alias</th>
                    <th className="py-2 font-mono text-xs text-[--text-muted]">Enabled</th>
                    <th className="py-2 font-mono text-xs text-[--text-muted]">File Pattern</th>
                    <th className="py-2 font-mono text-xs text-[--text-muted]">MTD Spend</th>
                    <th className="py-2 font-mono text-xs text-[--text-muted]">Budget</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.reviewers.map((r) => {
                    const spend = roleSpend[r.role];
                    const pct = spend && r.monthly_budget_cents
                      ? Math.min((spend.spend_cents / r.monthly_budget_cents) * 100, 100)
                      : 0;
                    return (
                      <tr key={r.role} className="border-b border-[--border] last:border-0">
                        <td className="py-2 font-mono text-xs text-[--text-m]">{r.role}</td>
                        <td className="py-2">
                          <span className="font-mono text-xs text-[--info] border border-[--border] px-1.5 py-0.5 rounded-[--radius-sm]">{r.model_alias}</span>
                        </td>
                        <td className="py-2">
                          {r.isolation ? (
                            <span className="font-mono text-xs text-[--success] bg-[--success-bg] border border-[--success-border] px-1.5 py-0.5 rounded-[--radius-sm]">enabled</span>
                          ) : (
                            <span className="font-mono text-xs text-[--text-muted] bg-[--surface-raised] border border-[--border] px-1.5 py-0.5 rounded-[--radius-sm]">disabled</span>
                          )}
                        </td>
                        <td className="py-2">
                          {r.file_patterns?.length ? (
                            <span className="font-mono text-xs text-[--info]">{r.file_patterns.join(", ")}</span>
                          ) : (
                            <span className="font-mono text-xs text-[--text-muted]">—</span>
                          )}
                        </td>
                        <td className="py-2 font-mono text-xs text-[--text-m]">
                          {spend ? formatCents(spend.spend_cents) : "—"}
                        </td>
                        <td className="py-2 w-32">
                          {r.monthly_budget_cents ? (
                            <div>
                              <Progress value={pct} className="h-1.5" />
                              <p className="font-mono text-xs text-[--text-muted] mt-0.5">
                                {formatCents(r.monthly_budget_cents)} cap
                              </p>
                            </div>
                          ) : (
                            <span className="font-mono text-xs text-[--text-muted]">No cap</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
