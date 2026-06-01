import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TaskCard } from "@/components/task/TaskCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { useTaskList } from "@/hooks/useTasks";
import type { TaskSummary, TaskStatus, PipelineStage } from "@/types/task";
import { STAGE_ORDER } from "@/types/task";

type ColumnKey = PipelineStage | "pushed" | "failed";

const COLUMNS: { key: ColumnKey; label: string }[] = [
  ...STAGE_ORDER.map((s) => ({ key: s as ColumnKey, label: s.charAt(0).toUpperCase() + s.slice(1) })),
  { key: "pushed", label: "Pushed" },
  { key: "failed", label: "Failed" },
];

const HITL_STATUSES: TaskStatus[] = [
  "needs_approval", "needs_clarification", "needs_step_recovery",
  "needs_review_recovery", "needs_timeout_recovery",
];

function taskColumn(task: TaskSummary): ColumnKey {
  if (task.status === "pushed") return "pushed";
  if (task.status === "stopped" || task.status === "push_failed" || task.status === "approval_rejected") return "failed";
  return task.next_stage;
}

/** Column header pip color — reflects the "hottest" status in the column */
function columnPip(tasks: TaskSummary[]): string {
  if (tasks.some((t) => t.status === "push_failed" || t.status === "approval_rejected")) return "var(--danger)";
  if (tasks.some((t) => HITL_STATUSES.includes(t.status))) return "var(--warning)";
  if (tasks.some((t) => t.status === "pushed")) return "var(--success)";
  if (tasks.some((t) => t.status === "running" || t.status === "pushing")) return "var(--accent)";
  return "var(--text-dim)";
}

type Filter = "all" | "running" | "hitl" | "failed";

const SECTION_LABEL: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "var(--text-xs)",
  color: "var(--text-dim)",
  textTransform: "uppercase",
};

export function BoardPage() {
  const { data, isLoading, error } = useTaskList();
  const [filter, setFilter] = useState<Filter>("all");

  const allTasks = data?.tasks ?? [];

  // Summary counts
  const running = allTasks.filter((t) => t.status === "running" || t.status === "pushing").length;
  const hitl = allTasks.filter((t) => HITL_STATUSES.includes(t.status)).length;
  const pushed = allTasks.filter((t) => t.status === "pushed").length;
  const failed = allTasks.filter((t) => t.status === "push_failed" || t.status === "stopped" || t.status === "approval_rejected").length;
  const total = allTasks.length;
  const sessionCents = allTasks.reduce((sum, t) => sum + (t.cost_cents_so_far ?? 0), 0);

  // Filter
  const visibleTasks = allTasks.filter((t) => {
    if (filter === "all") return true;
    if (filter === "running") return t.status === "running" || t.status === "pushing";
    if (filter === "hitl") return HITL_STATUSES.includes(t.status);
    if (filter === "failed") return t.status === "push_failed" || t.status === "stopped" || t.status === "approval_rejected";
    return true;
  });

  const tasksByColumn = COLUMNS.reduce<Record<string, TaskSummary[]>>(
    (acc, col) => ({ ...acc, [col.key]: [] }), {},
  );
  visibleTasks.forEach((task) => {
    const col = taskColumn(task);
    if (col in tasksByColumn) tasksByColumn[col].push(task);
  });

  const FilterChip = ({ value, label }: { value: Filter; label: string }) => (
    <button
      onClick={() => setFilter(value)}
      className="font-mono rounded-sm"
      style={{
        fontSize: "var(--text-xs)",
        padding: "3px 10px",
        cursor: "pointer",
        backgroundColor: filter === value ? "var(--accent-bg)" : "transparent",
        border: `1px solid ${filter === value ? "var(--accent-border)" : "var(--border-strong)"}`,
        color: filter === value ? "var(--accent)" : "var(--text-muted)",
      }}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Workshop Board"
        actions={
          <div className="flex items-center gap-2">
            <span className="animate-pulse" style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "var(--success)" }} />
            <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>live</span>
            <span style={{ width: 1, height: 16, background: "var(--border)", margin: "0 4px" }} />
            <FilterChip value="all" label="All" />
            <FilterChip value="running" label="Running" />
            <FilterChip value="hitl" label="HITL" />
            <FilterChip value="failed" label="Failed" />
            <span style={{ width: 1, height: 16, background: "var(--border)", margin: "0 4px" }} />
            <Button asChild size="sm" className="font-mono font-bold" style={{ fontSize: "var(--text-xs)", backgroundColor: "var(--accent)", color: "var(--background)" }}>
              <Link to="/launch">▶ LAUNCH TASK</Link>
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" style={{ color: "var(--text-dim)" }} />
        </div>
      ) : error ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="font-mono" style={{ fontSize: "var(--text-sm)", color: "var(--danger)" }}>Failed to load tasks</p>
        </div>
      ) : !total ? (
        <EmptyState
          title="No active tasks"
          description="Launch a build to get started"
          action={<Button asChild><Link to="/launch">Launch a build</Link></Button>}
        />
      ) : (
        <>
          {/* Summary strip */}
          <div
            className="flex items-center gap-4 px-6"
            style={{ height: 40, borderBottom: "1px solid var(--border)", backgroundColor: "var(--surface)", flexShrink: 0 }}
          >
            {[
              { v: running, l: "Running", c: "var(--accent)" },
              { v: hitl, l: "HITL", c: "var(--warning)" },
              { v: pushed, l: "Pushed", c: "var(--success)" },
              { v: failed, l: "Failed", c: "var(--danger)" },
              { v: total, l: "Total", c: "var(--text)" },
            ].map((s, i) => (
              <div key={s.l} className="flex items-center gap-2">
                {i > 0 && <span style={{ width: 1, height: 12, background: "var(--border)", marginRight: 8 }} />}
                <span className="font-mono" style={{ fontSize: "var(--text-md)", color: s.c }}>{s.v}</span>
                <span style={{ ...SECTION_LABEL }}>{s.l}</span>
              </div>
            ))}
            <span className="ml-auto font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>
              session ${(sessionCents / 100).toFixed(2)}
            </span>
          </div>

          {/* Board */}
          <div className="flex-1 overflow-x-auto" style={{ backgroundColor: "var(--background)" }}>
            <div className="flex h-full gap-3 p-4 min-w-max">
              {COLUMNS.map((col) => {
                const colTasks = tasksByColumn[col.key] ?? [];
                return (
                  <div key={col.key} className="flex flex-col gap-2" style={{ width: "200px" }}>
                    <div className="flex items-center justify-between px-1" style={{ paddingBottom: 8, borderBottom: "1px solid var(--border)" }}>
                      <div className="flex items-center gap-2">
                        <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: columnPip(colTasks) }} />
                        <span style={{ ...SECTION_LABEL, letterSpacing: "var(--tracking-wide)" }}>{col.label}</span>
                      </div>
                      <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: colTasks.length ? "var(--text-muted)" : "var(--text-dim)" }}>
                        {colTasks.length}
                      </span>
                    </div>
                    <ScrollArea className="flex-1">
                      <div className="flex flex-col gap-2">
                        {colTasks.map((task) => (
                          <TaskCard key={task.task_id} task={task} />
                        ))}
                        {colTasks.length === 0 && (
                          <p className="py-8 text-center font-mono" style={{ fontSize: "var(--text-xs)", border: "1px dashed var(--border)", color: "var(--text-dim)", borderRadius: "var(--radius-sm)" }}>
                            --empty--
                          </p>
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
