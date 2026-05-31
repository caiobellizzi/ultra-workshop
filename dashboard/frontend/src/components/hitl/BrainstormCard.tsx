import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { BrainstormPayload } from "@/types/task";

export function BrainstormCard({
  payload,
  onResolve,
  loading,
}: {
  payload: BrainstormPayload;
  onResolve: (decision: string) => void;
  loading?: boolean;
}) {
  return (
    <div
      className="rounded-sm"
      style={{
        border: "1px solid var(--warning-border)",
        borderTop: "2px solid var(--warning)",
        backgroundColor: "var(--surface)",
      }}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-2">
        <span
          className="text-xs tracking-widest uppercase font-mono"
          style={{ color: "var(--warning)" }}
        >
          ⌛ ACTION REQUIRED
        </span>
      </div>

      {/* Content */}
      <div className="px-4 pb-4 space-y-3">
        <p className="text-sm font-medium font-sans" style={{ color: "var(--text)" }}>
          {payload.goal_statement}
        </p>
        {payload.follow_up && (
          <p className="text-sm font-sans" style={{ color: "var(--text-muted)" }}>
            {payload.follow_up}
          </p>
        )}
        <div className="flex gap-2">
          <Button
            onClick={() => onResolve("approve")}
            disabled={loading}
            className="font-bold font-mono text-xs rounded-sm"
            style={{
              backgroundColor: "var(--accent)",
              color: "var(--bg)",
            }}
          >
            Approve
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                disabled={loading}
                className="font-mono text-xs rounded-sm"
                style={{
                  color: "var(--danger)",
                  borderColor: "var(--danger-border)",
                  backgroundColor: "var(--surface)",
                }}
              >
                Reject
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Reject Brainstorm</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure? This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => onResolve("reject")}>
                  Reject
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </div>
  );
}
