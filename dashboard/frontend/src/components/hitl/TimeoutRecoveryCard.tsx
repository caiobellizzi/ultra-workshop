import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          Timeout Recovery
          <Badge variant="outline">{payload.stage}</Badge>
          <Badge variant="secondary">Attempt {payload.attempt}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{payload.reason}</p>
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
