import { useNavigate } from "@tanstack/react-router";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { CostPill } from "@/components/shared/CostPill";
import type { TaskStatus, TaskSummary } from "@/types/task";
import { formatDuration, truncate } from "@/lib/utils";

interface TaskCardProps {
  task: TaskSummary;
}

/** Maps status to the left-border color token (matches StatusBadge text token) */
const STATUS_BORDER_COLOR: Record<TaskStatus, string> = {
  running:                "var(--accent)",
  needs_approval:         "var(--warning)",
  needs_clarification:    "var(--warning)",
  needs_step_recovery:    "var(--warning)",
  needs_review_recovery:  "var(--warning)",
  needs_timeout_recovery: "var(--warning)",
  stopped:                "var(--text-dim)",
  approval_rejected:      "var(--danger)",
  pushing:                "var(--accent)",
  pushed:                 "var(--success)",
  push_failed:            "var(--danger)",
};

export function TaskCard({ task }: TaskCardProps) {
  const navigate = useNavigate();
  const isHitl =
    task.status === "needs_approval" ||
    task.status === "needs_clarification" ||
    task.status === "needs_step_recovery" ||
    task.status === "needs_review_recovery" ||
    task.status === "needs_timeout_recovery";

  const borderColor = STATUS_BORDER_COLOR[task.status] ?? "var(--border)";

  return (
    <div
      className="cursor-pointer group"
      style={{
        width: "180px",
        backgroundColor: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `2px solid ${borderColor}`,
        borderRadius: "var(--radius-sm)",
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
        fontFamily: "var(--font-mono)",
      }}
      onClick={() => void navigate({ to: "/tasks/$taskId", params: { taskId: task.task_id } })}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-strong)";
        (e.currentTarget as HTMLDivElement).style.borderLeftColor = borderColor;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)";
        (e.currentTarget as HTMLDivElement).style.borderLeftColor = borderColor;
      }}
    >
      {/* Header row: task id + running indicator */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "4px" }}>
        <span
          style={{
            fontSize: "var(--text-xs)",
            color: "var(--text-muted)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {task.task_id.slice(0, 8)}
        </span>
        {task.status === "running" && (
          <span
            className="animate-pulse"
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: "var(--stage-running)",
              flexShrink: 0,
            }}
          />
        )}
        {(task.status === "needs_step_recovery" ||
          task.status === "needs_review_recovery" ||
          task.status === "needs_timeout_recovery") && (
          <span
            style={{
              fontSize: "var(--text-xs)",
              color: "var(--danger)",
              flexShrink: 0,
            }}
          >
            ✗
          </span>
        )}
        {(task.status === "needs_approval" || task.status === "needs_clarification") && (
          <span
            style={{
              fontSize: "var(--text-xs)",
              color: "var(--warning)",
              flexShrink: 0,
            }}
          >
            ⌛
          </span>
        )}
      </div>

      {/* Goal */}
      <p
        style={{
          fontSize: "var(--text-base)",
          color: "var(--text)",
          fontFamily: "var(--font-mono)",
          margin: 0,
          lineHeight: "1.4",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical" as const,
          overflow: "hidden",
        }}
      >
        {truncate(task.goal, 80)}
      </p>

      <StatusBadge status={task.status} />

      {task.current_step != null && task.total_steps != null && (
        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
          Step {task.current_step}/{task.total_steps}
        </span>
      )}

      {/* Meta row: cost · time */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <CostPill cents={task.cost_cents_so_far} />
        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
          {formatDuration(task.created_at)}
        </span>
      </div>

      {isHitl && (
        <button
          style={{
            width: "100%",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-xs)",
            color: "var(--warning)",
            backgroundColor: "var(--warning-bg)",
            border: "1px solid var(--warning-border)",
            borderRadius: "var(--radius-sm)",
            padding: "4px 12px",
            cursor: "pointer",
          }}
          onClick={(e) => {
            e.stopPropagation();
            void navigate({ to: "/hitl", search: { taskId: task.task_id } });
          }}
        >
          ⌛ Resolve
        </button>
      )}
    </div>
  );
}
