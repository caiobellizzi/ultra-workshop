import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PlanViewer } from "@/components/task/PlanViewer";
import type { ApprovalPayload } from "@/types/task";

interface ApprovalCardProps {
  taskId: string;
  payload: ApprovalPayload;
  onResolve: (decision: string, freeText?: string) => void;
  loading?: boolean;
}

export function ApprovalCard({ payload, onResolve, loading }: ApprovalCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Plan Approval</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <PlanViewer plan={payload.plan} />
        <div className="flex gap-2 pt-2">
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
