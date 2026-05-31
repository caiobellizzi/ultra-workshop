import { PageHeader } from "@/components/layout/PageHeader";
import { HITLCard } from "@/components/hitl/HITLCard";
import { useHITLQueue } from "@/hooks/useHITL";
import type { HITLPayload } from "@/types/task";

export function HITLQueuePage() {
  const { data, isLoading } = useHITLQueue();

  const count = data?.items.length ?? 0;

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Action Required"
        actions={
          count > 0 ? (
            <span
              style={{
                backgroundColor: "var(--danger-bg)",
                border: "1px solid var(--danger-border)",
                color: "var(--danger)",
                fontFamily: "var(--font-mono)",
                fontSize: "var(--text-xs)",
                borderRadius: "var(--radius-sm)",
                padding: "2px 6px",
              }}
            >
              {count}
            </span>
          ) : undefined
        }
      />
      <div className="flex-1 overflow-y-auto" style={{ padding: "24px" }}>
        {isLoading ? (
          /* Skeleton: 2 placeholder card outlines */
          <div className="flex flex-col gap-4" style={{ maxWidth: "672px", margin: "0 auto" }}>
            {[0, 1].map((i) => (
              <div
                key={i}
                className="animate-pulse"
                style={{
                  backgroundColor: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  borderTop: "2px solid var(--warning)",
                  borderRadius: "var(--radius-sm)",
                  height: "96px",
                }}
              />
            ))}
          </div>
        ) : count === 0 ? (
          <div
            className="flex items-center justify-center h-full"
            style={{ minHeight: "160px" }}
          >
            <span
              style={{
                color: "var(--text-dim)",
                fontFamily: "var(--font-mono)",
                fontSize: "var(--text-xs)",
              }}
            >
              -- no pending actions --
            </span>
          </div>
        ) : (
          <div className="flex flex-col gap-4" style={{ maxWidth: "672px", margin: "0 auto" }}>
            {data!.items.map((item) => (
              <div key={`${item.task_id}-${item.hitl_type}`}>
                <div
                  className="flex items-center gap-2"
                  style={{ marginBottom: "8px" }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--text-xs)",
                      color: "var(--text-muted)",
                    }}
                  >
                    {item.task_id}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--text-xs)",
                      color: "var(--text-dim)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius-sm)",
                      padding: "2px 6px",
                    }}
                  >
                    {item.hitl_type}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--text-xs)",
                      color: "var(--text-dim)",
                    }}
                  >
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
