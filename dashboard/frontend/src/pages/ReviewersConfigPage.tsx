import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
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

  const reviewers = data?.reviewers ?? [];
  const enabledCount = reviewers.filter((r) => r.isolation).length;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Reviewers Config"
        actions={
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-2 py-0.5 rounded-sm" style={{ color: "var(--info)", backgroundColor: "var(--info-bg)", border: "1px solid var(--info-border)" }}>
              {reviewers.length} roles defined
            </span>
          </div>
        }
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin" style={{ color: "var(--text-muted)" }} />
          </div>
        ) : (
          <>
            {/* Info note */}
            <div
              className="rounded-sm p-3 font-mono"
              style={{ fontSize: "var(--text-xs)", lineHeight: 1.6, color: "var(--text-muted)", backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
            >
              <span style={{ color: "var(--text)" }}>Trigger evaluation: </span>
              file patterns are matched against diff paths in each task commit. A reviewer runs when at least one
              changed file matches its configured pattern list. Disabled reviewers are skipped even if their patterns match.
            </div>

            <p className="font-mono uppercase" style={{ fontSize: "var(--text-xs)", letterSpacing: "var(--tracking-wide)", color: "var(--text-dim)" }}>
              Reviewer Roles &nbsp;·&nbsp; {enabledCount} enabled
            </p>

            <Card>
              <CardContent className="p-0">
                <table className="w-full">
                  <thead style={{ backgroundColor: "var(--surface)" }}>
                    <tr className="text-left" style={{ borderBottom: "1px solid var(--border)" }}>
                      <th className="py-2 px-3 font-mono uppercase" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.06em" }}>Role</th>
                      <th className="py-2 px-3 font-mono uppercase" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.06em" }}>File Pattern Triggers</th>
                      <th className="py-2 px-3 font-mono uppercase" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.06em" }}>Model</th>
                      <th className="py-2 px-3 font-mono uppercase" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.06em" }}>Enabled</th>
                      <th className="py-2 px-3 font-mono uppercase" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.06em" }}>MTD Spend</th>
                      <th className="py-2 px-3 font-mono uppercase w-32" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.06em" }}>Budget</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reviewers.map((r) => {
                      const spend = roleSpend[r.role];
                      const pct = spend && r.monthly_budget_cents
                        ? Math.min((spend.spend_cents / r.monthly_budget_cents) * 100, 100)
                        : 0;
                      return (
                        <tr key={r.role} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td className="py-2.5 px-3 font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text)" }}>{r.role}</td>
                          <td className="py-2.5 px-3">
                            <div className="flex flex-wrap gap-1">
                              {r.file_patterns?.length ? r.file_patterns.map((p) => (
                                <span key={p} className="font-mono px-1.5 py-0.5 rounded-sm" style={{ fontSize: "var(--text-xs)", color: "var(--info)", backgroundColor: "var(--info-bg)", border: "1px solid var(--info-border)" }}>{p}</span>
                              )) : <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>—</span>}
                            </div>
                          </td>
                          <td className="py-2.5 px-3 font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{r.model_alias}</td>
                          <td className="py-2.5 px-3">
                            {r.isolation ? (
                              <span className="font-mono px-1.5 py-0.5 rounded-sm" style={{ fontSize: "var(--text-xs)", color: "var(--success)", backgroundColor: "var(--success-bg)", border: "1px solid var(--success-border)" }}>ON</span>
                            ) : (
                              <span className="font-mono px-1.5 py-0.5 rounded-sm" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", backgroundColor: "var(--surface-raised)", border: "1px solid var(--border)" }}>OFF</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                            {spend ? formatCents(spend.spend_cents) : "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            {r.monthly_budget_cents ? (
                              <div>
                                <Progress value={pct} className="h-1.5" />
                                <p className="font-mono mt-0.5" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>
                                  {formatCents(r.monthly_budget_cents)} cap
                                </p>
                              </div>
                            ) : (
                              <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>No cap</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
