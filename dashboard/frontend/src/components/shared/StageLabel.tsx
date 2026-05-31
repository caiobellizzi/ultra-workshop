import type { PipelineStage } from "@/types/task";
import { cn } from "@/lib/utils";

const STAGE_PREFIX: Record<PipelineStage, string> = {
  brainstorm:   "◆ ",
  triage:       "▶ ",
  requirements: "▶ ",
  planner:      "▶ ",
  coder:        "▶ ",
  reviewer:     "▶ ",
  approval:     "○ ",
};

export function StageLabel({
  stage,
  className,
}: {
  stage: PipelineStage;
  className?: string;
}) {
  return (
    <span
      className={cn("inline-flex items-center capitalize", className)}
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-sm)",
        color: "var(--text-muted)",
      }}
    >
      {STAGE_PREFIX[stage] ?? "▶ "}{stage}
    </span>
  );
}
