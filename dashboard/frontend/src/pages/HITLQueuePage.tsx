import { Loader2, CheckCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { HITLCard } from "@/components/hitl/HITLCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Badge } from "@/components/ui/badge";
import { useHITLQueue } from "@/hooks/useHITL";
import type { HITLPayload } from "@/types/task";

export function HITLQueuePage() {
  const { data, isLoading } = useHITLQueue();

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="HITL Queue"
        description="Pending human-in-the-loop decisions"
        actions={
          data?.items.length ? (
            <Badge variant="destructive">{data.items.length} pending</Badge>
          ) : undefined
        }
      />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !data?.items.length ? (
          <EmptyState
            icon={<CheckCircle className="h-12 w-12" />}
            title="All clear"
            description="No pending decisions"
          />
        ) : (
          <div className="space-y-4 max-w-2xl mx-auto">
            {data.items.map((item) => (
              <div key={`${item.task_id}-${item.hitl_type}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono text-muted-foreground">{item.task_id}</span>
                  <Badge variant="outline">{item.hitl_type}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
                <HITLCard
                  taskId={item.task_id}
                  payload={{ ...item.payload, hitl_type: item.hitl_type } as HITLPayload}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
