import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          Review Recovery
          <Badge variant="outline">{payload.branch}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {payload.diff_summary && <p className="text-sm text-muted-foreground">{payload.diff_summary}</p>}
        {payload.blocking_issues.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground">Blocking Issues</p>
            {payload.blocking_issues.map((f, i) => (
              <div key={i} className="border rounded px-2 py-1 text-sm space-y-0.5">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={f.severity} />
                  <code className="text-xs">{f.file}</code>
                </div>
                <p>{f.problem}</p>
              </div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          {payload.options.map((opt, i) => (
            <button
              key={i}
              className={`w-full text-left text-sm border rounded-md px-3 py-2 transition-colors ${
                selected === opt ? "border-primary bg-primary/10" : "hover:bg-muted"
              }`}
              onClick={() => setSelected(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
        <Button disabled={!selected || loading} onClick={() => onResolve(selected)}>
          Submit
        </Button>
      </CardContent>
    </Card>
  );
}
