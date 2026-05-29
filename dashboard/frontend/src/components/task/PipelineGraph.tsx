import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, Circle, Loader2, AlertCircle, Clock } from "lucide-react";
import type { TaskDetail, PipelineStage, StageNodeStatus } from "@/types/task";
import { STAGE_ORDER } from "@/types/task";
import { StageLabel } from "@/components/shared/StageLabel";

function deriveStageStatus(task: TaskDetail, stage: PipelineStage): StageNodeStatus {
  const stageIdx = STAGE_ORDER.indexOf(stage);
  const currentIdx = STAGE_ORDER.indexOf(task.next_stage);

  if (stageIdx > currentIdx) return "pending";

  if (task.next_stage === stage) {
    if (task.status === "running") return "running";
    return "paused_hitl";
  }

  // Stage was passed — check if it has data
  if (stageIdx < currentIdx) {
    // Simple heuristic: if we passed it, it succeeded
    return "success";
  }

  return "pending";
}

interface StageNodeProps {
  stage: PipelineStage;
  status: StageNodeStatus;
  attempts: number;
  isCurrent: boolean;
  currentStep?: number | null;
  totalSteps?: number | null;
}

function StageNode({ stage, status, attempts, isCurrent, currentStep, totalSteps }: StageNodeProps) {
  const icons: Record<StageNodeStatus, React.ReactNode> = {
    pending: <Circle className="h-5 w-5 text-muted-foreground" />,
    running: <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />,
    success: <CheckCircle2 className="h-5 w-5 text-green-500" />,
    failed_retry: <XCircle className="h-5 w-5 text-amber-500" />,
    failed: <XCircle className="h-5 w-5 text-destructive" />,
    paused_hitl: <AlertCircle className="h-5 w-5 text-amber-500" />,
    skipped: <Clock className="h-5 w-5 text-muted-foreground opacity-40" />,
  };

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
        isCurrent && "bg-accent",
        status === "pending" && "opacity-50",
      )}
    >
      {icons[status]}
      <div className="flex-1 min-w-0">
        <StageLabel stage={stage} className="text-sm" />
        {attempts > 1 && (
          <span className="ml-1 text-xs text-muted-foreground">×{attempts}</span>
        )}
        {stage === "coder" && currentStep != null && totalSteps != null && (
          <div className="mt-1 h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${(currentStep / totalSteps) * 100}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export function PipelineGraph({ task }: { task: TaskDetail }) {
  return (
    <div className="flex flex-col">
      {STAGE_ORDER.map((stage, idx) => {
        const status = deriveStageStatus(task, stage);
        const isCurrent = task.next_stage === stage;
        return (
          <div key={stage}>
            <StageNode
              stage={stage}
              status={status}
              attempts={task.attempts[stage] ?? 0}
              isCurrent={isCurrent}
              currentStep={stage === "coder" ? task.current_step : undefined}
              totalSteps={stage === "coder" ? task.total_steps : undefined}
            />
            {idx < STAGE_ORDER.length - 1 && (
              <div className="ml-[22px] h-4 w-0.5 bg-border" />
            )}
          </div>
        );
      })}
    </div>
  );
}
