import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import type { ClarificationPayload } from "@/types/task";

interface ClarificationCardProps {
  payload: ClarificationPayload;
  onResolve: (decision: string, freeText?: string) => void;
  loading?: boolean;
}

export function ClarificationCard({ payload, onResolve, loading }: ClarificationCardProps) {
  const { request } = payload;
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [freeText, setFreeText] = useState("");

  const handleSubmit = () => {
    const parts = request.questions.map((_, i) => answers[i] ?? "").join("; ");
    const combined = freeText ? `${parts} | ${freeText}` : parts;
    onResolve(combined || "proceed");
  };

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
        <Badge variant="outline">{request.source_stage}</Badge>
      </div>

      {/* Content */}
      <div className="px-4 pb-4 space-y-4">
        <p className="text-sm font-sans" style={{ color: "var(--text-muted)" }}>
          {request.reason}
        </p>

        {request.questions.map((q, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-mono" style={{ color: "var(--text)" }}>
              {q}
            </p>
            {request.options[i]?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {request.options[i].map((opt) => (
                  <Button
                    key={opt}
                    size="sm"
                    variant="outline"
                    onClick={() => setAnswers((prev) => ({ ...prev, [i]: opt }))}
                    className="font-mono text-xs rounded-sm"
                    style={
                      answers[i] === opt
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
            )}
          </div>
        ))}

        {request.allow_free_text && (
          <Textarea
            placeholder="Additional context…"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
          />
        )}

        <Button
          onClick={handleSubmit}
          disabled={loading}
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
