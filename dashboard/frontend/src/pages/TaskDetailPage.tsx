import { useParams } from "@tanstack/react-router";
import { Loader2, ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { PipelineGraph } from "@/components/task/PipelineGraph";
import { StageOutputPane } from "@/components/task/StageOutputPane";
import { LogStream } from "@/components/task/LogStream";
import { HITLCard } from "@/components/hitl/HITLCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { CostPill } from "@/components/shared/CostPill";
import { useTask } from "@/hooks/useTasks";
import { formatDuration } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function TaskDetailPage() {
  // Use generic useParams — route tree puts params under the layout segment
  const params = useParams({ strict: false });
  const taskId = (params as { taskId?: string }).taskId ?? "";
  const { data: task, isLoading, error } = useTask(taskId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-destructive">Task not found or failed to load.</p>
      </div>
    );
  }

  const isHitl =
    task.status !== "running" &&
    task.status !== "pushed" &&
    task.status !== "stopped" &&
    task.approval_payload != null;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title={task.goal.slice(0, 60)}
        description={task.task_id}
        actions={<StatusBadge status={task.status} />}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left panel: pipeline graph + metadata */}
        <aside className="w-64 shrink-0 border-r flex flex-col overflow-y-auto">
          <div className="p-4 border-b">
            <PipelineGraph task={task} />
          </div>
          <div className="p-4 space-y-2 text-sm">
            {task.repo_full_name && (
              <a
                href={`https://github.com/${task.repo_full_name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-primary hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                {task.repo_full_name}
              </a>
            )}
            {task.default_branch && (
              <div>
                <span className="text-muted-foreground">Branch: </span>
                <Badge variant="outline">{task.default_branch}</Badge>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Elapsed: </span>
              {formatDuration(task.created_at)}
            </div>
            <div>
              <span className="text-muted-foreground">Cost: </span>
              <CostPill cents={task.cost_cents_so_far} />
            </div>
            {Object.entries(task.attempts).filter(([, v]) => v > 0).map(([stage, count]) => (
              <div key={stage}>
                <span className="text-muted-foreground">{stage}: </span>
                {count} attempt{count !== 1 ? "s" : ""}
              </div>
            ))}
          </div>
        </aside>

        {/* Center: stage outputs + logs */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4">
            <StageOutputPane task={task} />
          </div>
          <div className="border-t p-4">
            <LogStream taskId={taskId} />
          </div>
        </div>

        {/* Right panel: HITL (conditional) */}
        {isHitl && task.approval_payload && (
          <aside className="w-96 shrink-0 border-l overflow-y-auto p-4">
            <h3 className="text-sm font-semibold mb-3">Action Required</h3>
            <HITLCard taskId={taskId} payload={task.approval_payload} />
          </aside>
        )}
      </div>
    </div>
  );
}
