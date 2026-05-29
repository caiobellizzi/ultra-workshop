import { useNavigate } from "@tanstack/react-router";
import { Clock, AlertTriangle, Bell } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { CostPill } from "@/components/shared/CostPill";
import type { TaskSummary } from "@/types/task";
import { formatDuration, truncate } from "@/lib/utils";

interface TaskCardProps {
  task: TaskSummary;
}

export function TaskCard({ task }: TaskCardProps) {
  const navigate = useNavigate();
  const isHitl =
    task.status === "needs_approval" ||
    task.status === "needs_clarification" ||
    task.status === "needs_step_recovery" ||
    task.status === "needs_review_recovery" ||
    task.status === "needs_timeout_recovery";
  const isRecovery =
    task.status === "needs_step_recovery" ||
    task.status === "needs_review_recovery" ||
    task.status === "needs_timeout_recovery";

  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={() => void navigate({ to: "/tasks/$taskId", params: { taskId: task.task_id } })}
    >
      <CardContent className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <code className="text-xs text-muted-foreground truncate">{task.task_id.slice(0, 8)}</code>
          {task.status === "running" ? (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
            </span>
          ) : isRecovery ? (
            <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
          ) : isHitl ? (
            <Bell className="h-4 w-4 text-amber-500 shrink-0" />
          ) : null}
        </div>

        <p className="text-sm font-medium leading-snug">{truncate(task.goal, 80)}</p>

        <StatusBadge status={task.status} />

        {task.current_step != null && task.total_steps != null && (
          <p className="text-xs text-muted-foreground">
            Step {task.current_step}/{task.total_steps}
          </p>
        )}

        <div className="flex items-center justify-between pt-1">
          <CostPill cents={task.cost_cents_so_far} />
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {formatDuration(task.created_at)}
          </span>
        </div>

        {isHitl && (
          <Button
            size="sm"
            variant="outline"
            className="w-full mt-1"
            onClick={(e) => {
              e.stopPropagation();
              void navigate({ to: "/hitl", search: { taskId: task.task_id } });
            }}
          >
            Resolve
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
