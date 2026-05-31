import type { FindingSeverity } from "@/types/task";

const SEVERITY_CONFIG: Record<
  FindingSeverity,
  { text: string; bg: string; border: string; prefix: string }
> = {
  Critical:  { text: "var(--danger)",  bg: "var(--danger-bg)",  border: "var(--danger-border)",  prefix: "✗ " },
  Important: { text: "var(--warning)", bg: "var(--warning-bg)", border: "var(--warning-border)", prefix: "⌛ " },
  Minor:     { text: "var(--info)",    bg: "var(--info-bg)",    border: "var(--info-border)",    prefix: "○ " },
};

export function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  const cfg = SEVERITY_CONFIG[severity];
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
      {cfg.prefix}{severity}
    </span>
  );
}
