import { cn } from "@/lib/utils";

export function CostPill({ cents, className }: { cents: number; className?: string }) {
  const formatted =
    cents < 1 ? "$0.00" : cents < 100 ? `$${(cents / 100).toFixed(3)}` : `$${(cents / 100).toFixed(2)}`;
  return (
    <span
      className={cn("inline-flex items-center", className)}
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-xs)",
        color: "var(--text-muted)",
        backgroundColor: "var(--surface-raised)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: "2px 6px",
        whiteSpace: "nowrap",
      }}
    >
      {formatted}
    </span>
  );
}
