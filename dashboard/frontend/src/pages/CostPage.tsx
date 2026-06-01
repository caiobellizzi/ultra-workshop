import { useState, useMemo } from "react";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
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

const CHART_COLORS = ["var(--accent)", "var(--success)", "var(--info)", "var(--warning)", "var(--danger)"];

type Period = "7d" | "30d" | "90d" | "all";
const PERIOD_DAYS: Record<Period, number | null> = { "7d": 7, "30d": 30, "90d": 90, all: null };

export function CostPage() {
  const [period, setPeriod] = useState<Period>("30d");

  const { from, to } = useMemo(() => {
    const days = PERIOD_DAYS[period];
    if (days == null) return { from: undefined, to: undefined };
    const toD = new Date();
    const fromD = new Date(toD.getTime() - days * 86_400_000);
    return { from: fromD.toISOString().slice(0, 10), to: toD.toISOString().slice(0, 10) };
  }, [period]);

  const { data: summary, isLoading: loadingSummary } = useCostSummary(from, to);
  const { data: tasksData } = useCostTasks(from, to);
  const { data: trends } = useCostTrends(from, to);

  const dailyPct = summary
    ? Math.min((summary.today_cents / summary.daily_limit_cents) * 100, 100)
    : 0;

  const exportCsv = () => {
    const rows = tasksData?.tasks ?? [];
    const header = "task_id,goal,repo,date,total_cents\n";
    const body = rows.map((r) =>
      [r.task_id, JSON.stringify(r.goal ?? ""), r.repo, r.date, r.total_cents].join(",")
    ).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cost-${period}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const PeriodBtn = ({ value }: { value: Period }) => (
    <button
      onClick={() => setPeriod(value)}
      className="font-mono rounded-sm"
      style={{
        fontSize: "var(--text-xs)", padding: "3px 10px", cursor: "pointer",
        backgroundColor: period === value ? "var(--accent-bg)" : "transparent",
        border: `1px solid ${period === value ? "var(--accent-border)" : "var(--border-strong)"}`,
        color: period === value ? "var(--accent)" : "var(--text-muted)",
      }}
    >
      {value}
    </button>
  );

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Cost"
        actions={
          <div className="flex items-center gap-2">
            <PeriodBtn value="7d" />
            <PeriodBtn value="30d" />
            <PeriodBtn value="90d" />
            <PeriodBtn value="all" />
            <span style={{ width: 1, height: 16, background: "var(--border)", margin: "0 4px" }} />
            <button
              onClick={exportCsv}
              className="font-mono rounded-sm"
              style={{ fontSize: "var(--text-xs)", padding: "4px 10px", color: "var(--text-muted)", border: "1px solid var(--border-strong)", backgroundColor: "transparent", cursor: "pointer" }}
            >
              ↓ Export CSV
            </button>
          </div>
        }
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Summary cards */}
        {loadingSummary ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-[--surface] border border-[--border] rounded-sm p-4">
              <p className="text-xs text-[--text-muted] uppercase tracking-wide mb-2">Today</p>
              <p className="text-[--accent] font-mono text-xl">{formatCents(summary?.today_cents ?? 0)}</p>
              <Progress value={dailyPct} className="mt-2 h-2" />
              <p className="text-xs text-[--text-muted] mt-1">
                of {formatCents(summary?.daily_limit_cents ?? 2000)} limit
              </p>
            </div>
            <div className="bg-[--surface] border border-[--border] rounded-sm p-4">
              <p className="text-xs text-[--text-muted] uppercase tracking-wide mb-2">This Month</p>
              <p className="text-[--accent] font-mono text-xl">{formatCents(summary?.this_month_cents ?? 0)}</p>
            </div>
            <div className="bg-[--surface] border border-[--border] rounded-sm p-4">
              <p className="text-xs text-[--text-muted] uppercase tracking-wide mb-2">Per-Task Avg</p>
              <p className="text-[--accent] font-mono text-xl">{formatCents(summary?.per_task_avg_cents ?? 0)}</p>
            </div>
            <div className="bg-[--surface] border border-[--border] rounded-sm p-4">
              <p className="text-xs text-[--text-muted] uppercase tracking-wide mb-2">Top Model</p>
              <p className="font-mono text-[--text] truncate">{summary?.most_expensive_alias ?? "—"}</p>
            </div>
          </div>
        )}

        {/* Charts row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {trends?.daily && (
            <div className="bg-[--surface] border border-[--border] rounded-sm">
              <div className="px-4 py-3 border-b border-[--border]">
                <p className="text-xs text-[--text-muted] uppercase tracking-wide">Daily Spend (30d)</p>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={trends.daily.slice(-30)}>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `$${(v / 100).toFixed(0)}`} />
                    <Tooltip formatter={(v: number) => formatCents(v)} />
                    <Bar dataKey="cents" fill="var(--accent)" radius={2} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {trends?.by_model && (
            <div className="bg-[--surface] border border-[--border] rounded-sm">
              <div className="px-4 py-3 border-b border-[--border]">
                <p className="text-xs text-[--text-muted] uppercase tracking-wide">By Model (MTD)</p>
              </div>
              <div className="p-4">
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
              </div>
            </div>
          )}
        </div>

        {/* Per-build table */}
        {tasksData?.tasks && (
          <div className="bg-[--surface] border border-[--border] rounded-sm">
            <div className="px-4 py-3 border-b border-[--border]">
              <p className="text-xs text-[--text-muted] uppercase tracking-wide">Per-Build Costs</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="bg-[--surface] text-left">
                    <th className="py-2 px-4 text-[--text-dim] font-medium border-b border-[--border]">Task</th>
                    <th className="py-2 px-4 text-[--text-dim] font-medium border-b border-[--border]">Repo</th>
                    <th className="py-2 px-4 text-[--text-dim] font-medium border-b border-[--border]">Date</th>
                    <th className="py-2 px-4 text-[--text-dim] font-medium border-b border-[--border] text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {tasksData.tasks.map((row) => (
                    <tr key={row.task_id} className="border-b border-[--border] last:border-0">
                      <td className="py-2 px-4">
                        <span className="text-[--accent]">{row.task_id.slice(0, 8)}</span>
                        <p className="text-[--text-muted] truncate max-w-48">{row.goal}</p>
                      </td>
                      <td className="py-2 px-4 text-[--text-muted]">{row.repo}</td>
                      <td className="py-2 px-4 text-[--text-muted]">
                        {new Date(row.date).toLocaleDateString()}
                      </td>
                      <td className="py-2 px-4 text-right text-[--text]">{formatCents(row.total_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
