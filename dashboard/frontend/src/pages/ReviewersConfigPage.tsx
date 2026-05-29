import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Reviewer Roster</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium text-muted-foreground">Role</th>
                    <th className="pb-2 font-medium text-muted-foreground">Model Alias</th>
                    <th className="pb-2 font-medium text-muted-foreground">Isolation</th>
                    <th className="pb-2 font-medium text-muted-foreground">MTD Spend</th>
                    <th className="pb-2 font-medium text-muted-foreground">Budget</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.reviewers.map((r) => {
                    const spend = roleSpend[r.role];
                    const pct = spend && r.monthly_budget_cents
                      ? Math.min((spend.spend_cents / r.monthly_budget_cents) * 100, 100)
                      : 0;
                    return (
                      <tr key={r.role} className="border-b last:border-0">
                        <td className="py-2 font-medium">{r.role}</td>
                        <td className="py-2">
                          <Badge variant="outline" className="font-mono text-xs">{r.model_alias}</Badge>
                        </td>
                        <td className="py-2">
                          <Badge variant={r.isolation ? "secondary" : "outline"}>
                            {r.isolation ? "isolated" : "shared"}
                          </Badge>
                        </td>
                        <td className="py-2 text-xs">
                          {spend ? formatCents(spend.spend_cents) : "—"}
                        </td>
                        <td className="py-2 w-32">
                          {r.monthly_budget_cents ? (
                            <div>
                              <Progress value={pct} className="h-1.5" />
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {formatCents(r.monthly_budget_cents)} cap
                              </p>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">No cap</span>
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
