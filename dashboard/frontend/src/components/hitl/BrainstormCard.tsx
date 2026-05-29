import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { BrainstormPayload } from "@/types/task";

export function BrainstormCard({
  payload,
  onResolve,
  loading,
}: {
  payload: BrainstormPayload;
  onResolve: (decision: string) => void;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Brainstorm Review</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm font-medium">{payload.goal_statement}</p>
        {payload.follow_up && (
          <p className="text-sm text-muted-foreground">{payload.follow_up}</p>
        )}
        <div className="flex gap-2">
          <Button onClick={() => onResolve("approve")} disabled={loading}>
            Approve
          </Button>
          <Button variant="destructive" onClick={() => onResolve("reject")} disabled={loading}>
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
