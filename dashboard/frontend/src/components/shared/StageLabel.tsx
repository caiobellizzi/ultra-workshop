import {
  Brain,
  Filter,
  FileText,
  Map,
  Code2,
  Eye,
  CheckSquare,
} from "lucide-react";
import type { PipelineStage } from "@/types/task";
import { cn } from "@/lib/utils";

const STAGE_ICONS: Record<PipelineStage, React.ReactNode> = {
  brainstorm: <Brain className="h-4 w-4" />,
  triage: <Filter className="h-4 w-4" />,
  requirements: <FileText className="h-4 w-4" />,
  planner: <Map className="h-4 w-4" />,
  coder: <Code2 className="h-4 w-4" />,
  reviewer: <Eye className="h-4 w-4" />,
  approval: <CheckSquare className="h-4 w-4" />,
};

export function StageLabel({
  stage,
  className,
}: {
  stage: PipelineStage;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1 font-medium capitalize", className)}>
      {STAGE_ICONS[stage]}
      {stage}
    </span>
  );
}
