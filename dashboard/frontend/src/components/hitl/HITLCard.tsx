import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tasks as tasksApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { ApprovalCard } from "./ApprovalCard";
import { ClarificationCard } from "./ClarificationCard";
import { StepRecoveryCard } from "./StepRecoveryCard";
import { ReviewRecoveryCard } from "./ReviewRecoveryCard";
import { TimeoutRecoveryCard } from "./TimeoutRecoveryCard";
import { BrainstormCard } from "./BrainstormCard";
import type { HITLPayload } from "@/types/task";
import { Card, CardContent } from "@/components/ui/card";

interface HITLCardProps {
  taskId: string;
  payload: HITLPayload;
}

export function HITLCard({ taskId, payload }: HITLCardProps) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ decision, freeText }: { decision: string; freeText?: string }) =>
      tasksApi.resolveHitl(taskId, { decision, free_text: freeText }),
    onSuccess: () => {
      toast({ title: "HITL resolved", description: "Decision submitted." });
      void queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      void queryClient.invalidateQueries({ queryKey: ["hitl"] });
    },
    onError: (err) => {
      toast({ variant: "destructive", title: "Failed", description: String(err) });
    },
  });

  const resolve = (decision: string, freeText?: string) => {
    mutation.mutate({ decision, freeText });
  };

  switch (payload.hitl_type) {
    case "approval":
      return <ApprovalCard taskId={taskId} payload={payload} onResolve={resolve} loading={mutation.isPending} />;
    case "clarification":
      return <ClarificationCard payload={payload} onResolve={resolve} loading={mutation.isPending} />;
    case "step_retry_exhausted":
      return <StepRecoveryCard payload={payload} onResolve={resolve} loading={mutation.isPending} />;
    case "review_retry_exhausted":
      return <ReviewRecoveryCard payload={payload} onResolve={resolve} loading={mutation.isPending} />;
    case "timeout_recovery":
      return <TimeoutRecoveryCard payload={payload} onResolve={resolve} loading={mutation.isPending} />;
    case "brainstorm":
      return <BrainstormCard payload={payload} onResolve={resolve} loading={mutation.isPending} />;
    default: {
      // Unknown HITL type — render raw JSON fallback
      const unknown = payload as HITLPayload & { hitl_type: string };
      return (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground mb-2">Unknown HITL type: {unknown.hitl_type}</p>
            <pre className="text-xs bg-muted p-2 rounded-md overflow-auto max-h-64">
              {JSON.stringify(payload, null, 2)}
            </pre>
          </CardContent>
        </Card>
      );
    }
  }
}
