import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { TimeoutRecoveryPayload } from "@/types/task";

export function TimeoutRecoveryCard({
  payload,
  onResolve,
  loading,
}: {
  payload: TimeoutRecoveryPayload;
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
        <Badge variant="outline">{payload.stage}</Badge>
        <Badge variant="secondary">Attempt {payload.attempt}</Badge>
      </div>

      {/* Content */}
      <div className="px-4 pb-4 space-y-3">
        <p className="text-sm font-sans" style={{ color: "var(--text-muted)" }}>
          {payload.reason}
        </p>
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
