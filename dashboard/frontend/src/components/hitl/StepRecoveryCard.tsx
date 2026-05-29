import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { StepRetryPayload } from "@/types/task";

export function StepRecoveryCard({
  payload,
  onResolve,
  loading,
}: {
  payload: StepRetryPayload;
  onResolve: (decision: string) => void;
  loading?: boolean;
}) {
  const [selected, setSelected] = useState<string>("");
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Step Recovery Needed</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">
          <span className="font-medium">Step {payload.step_idx}:</span> {payload.step_desc}
        </p>
        {payload.reason && <p className="text-sm text-muted-foreground">{payload.reason}</p>}
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
