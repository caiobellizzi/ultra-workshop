import { FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Plan } from "@/types/task";

export function PlanViewer({ plan }: { plan: Plan }) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-semibold text-muted-foreground mb-1">Goal</h4>
        <p className="text-sm">{plan.goal}</p>
      </div>

      {plan.affected_files.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-muted-foreground mb-2">Affected Files</h4>
          <div className="flex flex-wrap gap-1">
            {plan.affected_files.map((f) => (
              <code key={f} className="text-xs bg-muted px-1.5 py-0.5 rounded">
                {f}
              </code>
            ))}
          </div>
        </div>
      )}

      <div>
        <h4 className="text-sm font-semibold text-muted-foreground mb-2">Steps</h4>
        <div className="space-y-2">
          {plan.steps.map((step, i) => (
            <Card key={step.id}>
              <CardHeader className="pb-2 pt-3 px-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold shrink-0">
                    {i + 1}
                  </span>
                  {step.description}
                </CardTitle>
              </CardHeader>
              {(step.files.length > 0 || step.model_alias) && (
                <CardContent className="px-4 pb-3">
                  <div className="flex flex-wrap gap-1">
                    {step.files.map((f) => (
                      <span key={f} className="flex items-center gap-1 text-xs text-muted-foreground">
                        <FileText className="h-3 w-3" />
                        {f}
                      </span>
                    ))}
                    {step.model_alias && (
                      <Badge variant="outline" className="text-xs">
                        {step.model_alias}
                      </Badge>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
