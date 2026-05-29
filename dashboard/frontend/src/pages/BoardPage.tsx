import { Loader2, Rocket } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TaskCard } from "@/components/task/TaskCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { useTaskList } from "@/hooks/useTasks";
import type { TaskSummary, PipelineStage } from "@/types/task";
import { STAGE_ORDER } from "@/types/task";

const COLUMNS: { key: PipelineStage | "done" | "failed"; label: string }[] = [
  ...STAGE_ORDER.map((s) => ({ key: s as PipelineStage | "done" | "failed", label: s.charAt(0).toUpperCase() + s.slice(1) })),
  { key: "done", label: "Done" },
  { key: "failed", label: "Failed" },
];

function taskColumn(task: TaskSummary): string {
  if (task.status === "pushed" || task.status === "approval_rejected") return "done";
  if (task.status === "stopped" || task.status === "push_failed") return "failed";
  return task.next_stage;
}

export function BoardPage() {
  const { data, isLoading, error } = useTaskList();

  const tasksByColumn = COLUMNS.reduce<Record<string, TaskSummary[]>>(
    (acc, col) => ({ ...acc, [col.key]: [] }),
    {},
  );
  data?.tasks.forEach((task) => {
    const col = taskColumn(task);
    if (col in tasksByColumn) {
      tasksByColumn[col].push(task);
    }
  });

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Live Board"
        description="Active pipeline tasks"
        actions={
          <Button asChild size="sm">
            <Link to="/launch">
              <Rocket className="h-4 w-4" />
              Launch
            </Link>
          </Button>
        }
      />
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-destructive">Failed to load tasks</p>
        </div>
      ) : !data?.tasks.length ? (
        <EmptyState
          title="No active tasks"
          description="Launch a build to get started"
          action={
            <Button asChild>
              <Link to="/launch">Launch a build</Link>
            </Button>
          }
        />
      ) : (
        <div className="flex-1 overflow-x-auto">
          <div className="flex h-full gap-3 p-4 min-w-max">
            {COLUMNS.map((col) => (
              <div key={col.key} className="flex w-56 flex-col gap-2">
                <div className="flex items-center justify-between px-1">
                  <h3 className="text-sm font-semibold capitalize">{col.label}</h3>
                  <span className="text-xs text-muted-foreground">
                    {tasksByColumn[col.key]?.length ?? 0}
                  </span>
                </div>
                <ScrollArea className="flex-1 rounded-md border bg-muted/20 p-2">
                  <div className="space-y-2">
                    {tasksByColumn[col.key]?.map((task) => (
                      <TaskCard key={task.task_id} task={task} />
                    ))}
                    {tasksByColumn[col.key]?.length === 0 && (
                      <p className="py-8 text-center text-xs text-muted-foreground">Empty</p>
                    )}
                  </div>
                </ScrollArea>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
