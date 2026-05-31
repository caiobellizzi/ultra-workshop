import type { TaskStatus } from "@/types/task";

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; prefix: string; text: string; bg: string; border: string }
> = {
  running:                { label: "Running",           prefix: "● ", text: "var(--accent)",    bg: "var(--accent-bg)",    border: "var(--accent-border)"  },
  needs_approval:         { label: "Needs Approval",    prefix: "⌛ ", text: "var(--warning)",   bg: "var(--warning-bg)",   border: "var(--warning-border)" },
  needs_clarification:    { label: "Needs Clarify",     prefix: "⌛ ", text: "var(--warning)",   bg: "var(--warning-bg)",   border: "var(--warning-border)" },
  needs_step_recovery:    { label: "Step Recovery",     prefix: "⌛ ", text: "var(--warning)",   bg: "var(--warning-bg)",   border: "var(--warning-border)" },
  needs_review_recovery:  { label: "Review Recovery",   prefix: "⌛ ", text: "var(--warning)",   bg: "var(--warning-bg)",   border: "var(--warning-border)" },
  needs_timeout_recovery: { label: "Timeout Recovery",  prefix: "⌛ ", text: "var(--warning)",   bg: "var(--warning-bg)",   border: "var(--warning-border)" },
  stopped:                { label: "Stopped",           prefix: "",    text: "var(--text-muted)", bg: "var(--surface-raised)", border: "var(--border)"        },
  approval_rejected:      { label: "Rejected",          prefix: "✗ ", text: "var(--danger)",    bg: "var(--danger-bg)",    border: "var(--danger-border)"  },
  pushing:                { label: "Pushing",           prefix: "↑ ", text: "var(--accent)",    bg: "var(--accent-bg)",    border: "var(--accent-border)"  },
  pushed:                 { label: "Pushed",            prefix: "✓ ", text: "var(--success)",   bg: "var(--success-bg)",   border: "var(--success-border)" },
  push_failed:            { label: "Push Failed",       prefix: "✗ ", text: "var(--danger)",    bg: "var(--danger-bg)",    border: "var(--danger-border)"  },
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  const cfg = STATUS_CONFIG[status] ?? {
    label: status,
    prefix: "○ ",
    text: "var(--text-dim)",
    bg: "var(--surface)",
    border: "var(--border)",
  };
  return (
    <span
      style={{
        color: cfg.text,
        backgroundColor: cfg.bg,
        borderColor: cfg.border,
        borderRadius: "var(--radius-sm)",
        fontSize: "var(--text-xs)",
        fontFamily: "var(--font-mono)",
        border: `1px solid ${cfg.border}`,
        padding: "2px 6px",
        display: "inline-flex",
        alignItems: "center",
        whiteSpace: "nowrap" as const,
      }}
    >
      {cfg.prefix}{cfg.label}
    </span>
  );
}
