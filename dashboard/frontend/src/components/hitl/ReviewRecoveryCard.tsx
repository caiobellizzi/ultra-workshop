import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import type { ReviewRetryPayload } from "@/types/task";

export function ReviewRecoveryCard({
  payload,
  onResolve,
  loading,
}: {
  payload: ReviewRetryPayload;
  onResolve: (decision: string) => void;
  loading?: boolean;
}) {
  const [selected, setSelected] = useState("");

  return (
    <div
      className="rounded-sm"
      style={{
        border: "1px solid var(--warning-border)",
        borderTop: "2px solid var(--warning)",
        backgroundColor: "var(--surface)",
      }}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-2 flex items-center gap-2">
        <span
          className="text-xs tracking-widest uppercase font-mono"
          style={{ color: "var(--warning)" }}
        >
          ⌛ ACTION REQUIRED
        </span>
        <Badge variant="outline">{payload.branch}</Badge>
      </div>

      {/* Content */}
      <div className="px-4 pb-4 space-y-3">
        {payload.diff_summary && (
          <p className="text-sm font-sans" style={{ color: "var(--text-muted)" }}>
            {payload.diff_summary}
          </p>
        )}
        {payload.blocking_issues.length > 0 && (
          <div className="space-y-1">
            <p
              className="text-xs font-semibold font-mono tracking-widest uppercase"
              style={{ color: "var(--text-muted)" }}
            >
              Blocking Issues
            </p>
            {payload.blocking_issues.map((f, i) => (
              <div
                key={i}
                className="px-2 py-1 text-sm space-y-0.5 rounded-sm"
                style={{ border: "1px solid var(--border)" }}
              >
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={f.severity} />
                  <code className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                    {f.file}
                  </code>
                </div>
                <p className="font-sans text-sm" style={{ color: "var(--text)" }}>
                  {f.problem}
                </p>
              </div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          {payload.options.map((opt, i) => (
            <Button
              key={i}
              variant="outline"
              onClick={() => setSelected(opt)}
              className="w-full justify-start font-mono text-xs rounded-sm"
              style={
                selected === opt
                  ? {
                      backgroundColor: "var(--accent-bg)",
                      borderColor: "var(--accent)",
                      color: "var(--accent)",
                    }
                  : {
                      borderColor: "var(--border-s)",
                      color: "var(--text-m)",
                    }
              }
            >
              {opt}
            </Button>
          ))}
        </div>
        <Button
          disabled={!selected || loading}
          onClick={() => onResolve(selected)}
          className="font-bold font-mono text-xs rounded-sm"
          style={{
            backgroundColor: "var(--accent)",
            color: "var(--bg)",
          }}
        >
          Submit
        </Button>
      </div>
    </div>
  );
}
