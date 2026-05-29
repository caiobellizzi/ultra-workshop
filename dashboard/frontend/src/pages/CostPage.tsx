import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useCostSummary, useCostTasks, useCostTrends } from "@/hooks/useCost";
import { formatCents } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export function CostPage() {
  const { data: summary, isLoading: loadingSummary } = useCostSummary();
  const { data: tasksData } = useCostTasks();
  const { data: trends } = useCostTrends();

  const dailyPct = summary
    ? Math.min((summary.today_cents / summary.daily_limit_cents) * 100, 100)
    : 0;

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Cost Analytics" description="Spending overview" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Summary cards */}
        {loadingSummary ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Today</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{formatCents(summary?.today_cents ?? 0)}</p>
                <Progress value={dailyPct} className="mt-2 h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  of {formatCents(summary?.daily_limit_cents ?? 2000)} limit
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">This Month</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{formatCents(summary?.this_month_cents ?? 0)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Per-Task Avg</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{formatCents(summary?.per_task_avg_cents ?? 0)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">Top Model</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium truncate">{summary?.most_expensive_alias ?? "—"}</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Charts row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {trends?.daily && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Daily Spend (30d)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={trends.daily.slice(-30)}>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `$${(v / 100).toFixed(0)}`} />
                    <Tooltip formatter={(v: number) => formatCents(v)} />
                    <Bar dataKey="cents" fill="#3b82f6" radius={2} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {trends?.by_model && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By Model (MTD)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={trends.by_model}
                      dataKey="cents"
                      nameKey="alias"
                      cx="50%"
                      cy="50%"
                      outerRadius={70}
                    >
                      {trends.by_model.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => formatCents(v)} />
                    <Legend iconSize={10} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Per-build table */}
        {tasksData?.tasks && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Per-Build Costs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium text-muted-foreground">Task</th>
                      <th className="pb-2 font-medium text-muted-foreground">Repo</th>
                      <th className="pb-2 font-medium text-muted-foreground">Date</th>
                      <th className="pb-2 font-medium text-muted-foreground text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasksData.tasks.map((row) => (
                      <tr key={row.task_id} className="border-b last:border-0">
                        <td className="py-2">
                          <code className="text-xs">{row.task_id.slice(0, 8)}</code>
                          <p className="text-xs text-muted-foreground truncate max-w-48">{row.goal}</p>
                        </td>
                        <td className="py-2 text-xs text-muted-foreground">{row.repo}</td>
                        <td className="py-2 text-xs text-muted-foreground">
                          {new Date(row.date).toLocaleDateString()}
                        </td>
                        <td className="py-2 text-right font-medium">{formatCents(row.total_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
