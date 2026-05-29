import { Badge } from "@/components/ui/badge";
import type { TaskStatus } from "@/types/task";

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" }
> = {
  running: { label: "Running", variant: "info" },
  needs_approval: { label: "Needs Approval", variant: "warning" },
  needs_clarification: { label: "Needs Clarification", variant: "warning" },
  needs_step_recovery: { label: "Step Recovery", variant: "destructive" },
  needs_review_recovery: { label: "Review Recovery", variant: "destructive" },
  needs_timeout_recovery: { label: "Timeout Recovery", variant: "destructive" },
  stopped: { label: "Stopped", variant: "secondary" },
  approval_rejected: { label: "Rejected", variant: "destructive" },
  pushing: { label: "Pushing", variant: "info" },
  pushed: { label: "Pushed", variant: "success" },
  push_failed: { label: "Push Failed", variant: "destructive" },
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, variant: "outline" as const };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}
