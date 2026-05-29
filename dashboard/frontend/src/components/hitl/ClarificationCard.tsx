import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          Clarification Needed
          <Badge variant="outline">{request.source_stage}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{request.reason}</p>

        {request.questions.map((q, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-medium">{q}</p>
            {request.options[i]?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {request.options[i].map((opt) => (
                  <Button
                    key={opt}
                    size="sm"
                    variant={answers[i] === opt ? "default" : "outline"}
                    onClick={() => setAnswers((prev) => ({ ...prev, [i]: opt }))}
                  >
                    {opt}
                  </Button>
                ))}
              </div>
            )}
          </div>
        ))}

        {request.allow_free_text && (
          <textarea
            className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[80px]"
            placeholder="Additional context…"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
          />
        )}

        <Button onClick={handleSubmit} disabled={loading}>
          Submit
        </Button>
      </CardContent>
    </Card>
  );
}
