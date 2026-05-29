import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PlanViewer } from "./PlanViewer";
import { DiffViewer } from "./DiffViewer";
import { ReviewWaveTable } from "./ReviewWaveTable";
import type { TaskDetail } from "@/types/task";

export function StageOutputPane({ task }: { task: TaskDetail }) {
  const { stages } = task;
  const hasTriage = !!stages.triage;
  const hasRequirements = !!stages.requirements;
  const hasPlan = !!stages.planner;
  const hasDiff = !!stages.diff;
  const hasReview = !!(stages.wave_reports || stages.merge_report);

  const defaultTab = hasDiff
    ? "coder"
    : hasReview
    ? "reviewer"
    : hasPlan
    ? "planner"
    : hasRequirements
    ? "requirements"
    : hasTriage
    ? "triage"
    : "triage";

  return (
    <Tabs defaultValue={defaultTab} className="w-full">
      <TabsList className="flex-wrap h-auto gap-1">
        {hasTriage && <TabsTrigger value="triage">Triage</TabsTrigger>}
        {hasRequirements && <TabsTrigger value="requirements">Requirements</TabsTrigger>}
        {hasPlan && <TabsTrigger value="planner">Plan</TabsTrigger>}
        {hasDiff && <TabsTrigger value="coder">Coder / Diff</TabsTrigger>}
        {hasReview && <TabsTrigger value="reviewer">Reviewer</TabsTrigger>}
        {task.approval_payload && <TabsTrigger value="approval">Approval</TabsTrigger>}
      </TabsList>

      {hasTriage && stages.triage && (
        <TabsContent value="triage" className="p-4 space-y-2">
          <div className="text-sm space-y-1">
            <p><span className="font-medium">Type:</span> {stages.triage.task_type}</p>
            <p><span className="font-medium">Complexity:</span> {stages.triage.complexity}</p>
            <p className="text-muted-foreground">{stages.triage.summary}</p>
          </div>
        </TabsContent>
      )}

      {hasRequirements && stages.requirements && (
        <TabsContent value="requirements" className="p-4 space-y-2">
          <div className="text-sm">
            <p className="font-medium">Ready: {stages.requirements.ready ? "Yes" : "No"}</p>
            <p className="text-muted-foreground mt-1">{stages.requirements.context}</p>
          </div>
        </TabsContent>
      )}

      {hasPlan && stages.planner && (
        <TabsContent value="planner" className="p-4">
          <PlanViewer plan={stages.planner} />
        </TabsContent>
      )}

      {hasDiff && stages.diff && (
        <TabsContent value="coder" className="p-4">
          <DiffViewer diff={stages.diff} />
        </TabsContent>
      )}

      {hasReview && (
        <TabsContent value="reviewer" className="p-4">
          <ReviewWaveTable waveReports={stages.wave_reports} mergeReport={stages.merge_report} />
        </TabsContent>
      )}

      {task.approval_payload && (
        <TabsContent value="approval" className="p-4">
          <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-64">
            {JSON.stringify(task.approval_payload, null, 2)}
          </pre>
        </TabsContent>
      )}
    </Tabs>
  );
}
