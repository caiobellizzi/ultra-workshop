import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { repos as reposApi, tasks as tasksApi, hitl as hitlApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type { TaskSummary } from "@/types/task";

const SECTION_LABEL: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "var(--text-xs)",
  letterSpacing: "var(--tracking-wide)",
  textTransform: "uppercase",
  color: "var(--text-dim)",
};

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function LaunchPage() {
  const navigate = useNavigate();
  const [repo, setRepo] = useState("");
  const [goal, setGoal] = useState("");
  const [brainstorm, setBrainstorm] = useState(false);

  const { data: reposData } = useQuery({
    queryKey: ["repos"],
    queryFn: () => reposApi.list(),
  });

  const { data: recentData } = useQuery({
    queryKey: ["tasks", { limit: 5 }],
    queryFn: () => tasksApi.list({ limit: 5 }),
  });

  const { data: hitlData } = useQuery({
    queryKey: ["hitl"],
    queryFn: () => hitlApi.list(),
  });

  const activeRepos = reposData?.repos.filter((r) => r.active) ?? [];
  const recentTasks: TaskSummary[] = recentData?.tasks ?? [];
  const runningCount = recentTasks.filter((t) => t.status === "running").length;
  const hitlCount = hitlData?.items.length ?? 0;

  const launchMutation = useMutation({
    mutationFn: () => tasksApi.create({ repo, goal, brainstorm }),
    onSuccess: async (data) => {
      toast({ title: "Build launched", description: data.task_id });
      await navigate({ to: "/tasks/$taskId", params: { taskId: data.task_id } });
    },
    onError: (e) => toast({ variant: "destructive", title: "Launch failed", description: String(e) }),
  });

  const canSubmit = repo && goal.length >= 10;

  const reset = () => {
    setGoal("");
    setBrainstorm(false);
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Launch Task" description="dispatch a new agent job" />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid gap-5 items-start" style={{ gridTemplateColumns: "minmax(0,1fr) 280px" }}>

          {/* ── LEFT: form ── */}
          <div>
            <p style={{ ...SECTION_LABEL, marginBottom: 12 }}>Task definition</p>

            <div
              className="rounded-sm p-4"
              style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
            >
              {/* Goal */}
              <div className="mb-5">
                <Label className="font-mono mb-1 block" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                  Goal <span style={{ color: "var(--danger)" }}>*</span>
                </Label>
                <Textarea
                  placeholder={"Describe the task for the AI coder…\n\nBe specific. Include acceptance criteria, constraints, and relevant file paths when known."}
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  className="min-h-[160px]"
                  style={{ lineHeight: 1.6 }}
                />
                <p className="font-mono mt-1" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>
                  {goal.length} chars (min 10)
                </p>
              </div>

              <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" }} />

              {/* Repository (wired) */}
              <div className="mb-5">
                <Label className="font-mono mb-1 block" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                  Repository
                </Label>
                <Select value={repo} onValueChange={setRepo}>
                  <SelectTrigger
                    className="font-mono rounded-sm h-8"
                    style={{ fontSize: "var(--text-xs)", backgroundColor: "var(--surface-raised)", border: "1px solid var(--border-strong)", color: "var(--text)" }}
                  >
                    <SelectValue placeholder="select a repo…" />
                  </SelectTrigger>
                  <SelectContent style={{ backgroundColor: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
                    {activeRepos.map((r) => (
                      <SelectItem key={r.full_name} value={r.full_name} className="font-mono" style={{ fontSize: "var(--text-xs)" }}>
                        {r.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" }} />

              {/* Options */}
              <div>
                <Label className="font-mono mb-3 block" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>
                  Options
                </Label>
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <Checkbox
                    id="brainstorm"
                    checked={brainstorm}
                    onCheckedChange={(c) => setBrainstorm(c === true)}
                    className="mt-0.5"
                  />
                  <span className="flex flex-col gap-0.5">
                    <span className="font-mono" style={{ fontSize: "var(--text-sm)", color: "var(--text)" }}>
                      Enable brainstorm stage
                    </span>
                    <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)", lineHeight: 1.4 }}>
                      Run an upfront brainstorm pass to refine the goal before triage.
                    </span>
                  </span>
                </label>
              </div>
            </div>

            {/* Action row */}
            <div className="flex items-center gap-2.5 mt-4">
              <Button
                className="font-mono font-bold rounded-sm"
                style={{
                  fontSize: "var(--text-sm)", padding: "9px 20px", letterSpacing: "var(--tracking-wide)",
                  backgroundColor: canSubmit && !launchMutation.isPending ? "var(--accent)" : "var(--accent-dim)",
                  color: "var(--background)", border: "none",
                }}
                onClick={() => launchMutation.mutate()}
                disabled={!canSubmit || launchMutation.isPending}
              >
                {launchMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                ▶ LAUNCH
              </Button>
              <Button
                variant="outline"
                className="font-mono rounded-sm"
                style={{ fontSize: "var(--text-xs)", padding: "8px 14px", color: "var(--text-muted)", border: "1px solid var(--border-strong)", backgroundColor: "transparent" }}
                onClick={reset}
              >
                ✕ clear
              </Button>
            </div>
          </div>

          {/* ── RIGHT: recent tasks + queue ── */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <p style={{ ...SECTION_LABEL }}>Recent tasks</p>
              <button
                className="font-mono"
                style={{ fontSize: "var(--text-xs)", color: "var(--accent-dim)", background: "none", border: "none", cursor: "pointer" }}
                onClick={() => navigate({ to: "/" })}
              >
                view all →
              </button>
            </div>

            {recentTasks.length === 0 ? (
              <div
                className="rounded-sm flex items-center justify-center font-mono"
                style={{ border: "1px dashed var(--border)", color: "var(--text-dim)", fontSize: "var(--text-xs)", padding: "24px 0" }}
              >
                -- no recent tasks --
              </div>
            ) : (
              recentTasks.map((t) => (
                <button
                  key={t.task_id}
                  onClick={() => navigate({ to: "/tasks/$taskId", params: { taskId: t.task_id } })}
                  className="w-full text-left rounded-sm p-3 mb-2.5 block"
                  style={{ border: "1px solid var(--border)", backgroundColor: "var(--surface-raised)", cursor: "pointer" }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>
                      #{t.task_id.slice(0, 8)}
                    </span>
                    <StatusBadge status={t.status} />
                  </div>
                  <div
                    className="font-mono mb-2"
                    style={{ fontSize: "var(--text-xs)", color: "var(--text)", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}
                  >
                    {t.goal}
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>
                    <span>{t.repo_full_name?.split("/").pop() ?? t.repo}</span>
                    <span style={{ width: 1, height: 10, background: "var(--border)" }} />
                    <span>{timeAgo(t.updated_at)}</span>
                  </div>
                </button>
              ))
            )}

            <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "16px 0" }} />

            <p style={{ ...SECTION_LABEL, marginBottom: 12 }}>Queue</p>
            <div className="rounded-sm p-3" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>running</span>
                  <span className="font-mono" style={{ fontSize: "var(--text-sm)", color: "var(--accent)" }}>{runningCount}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}>hitl pending</span>
                  <span className="font-mono" style={{ fontSize: "var(--text-sm)", color: "var(--warning)" }}>{hitlCount}</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
