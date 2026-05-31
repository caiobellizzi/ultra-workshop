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
import { repos as reposApi, tasks as tasksApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

export function LaunchPage() {
  const navigate = useNavigate();
  const [repo, setRepo] = useState("");
  const [goal, setGoal] = useState("");
  const [brainstorm, setBrainstorm] = useState(false);

  const { data: reposData } = useQuery({
    queryKey: ["repos"],
    queryFn: () => reposApi.list(),
  });

  const activeRepos = reposData?.repos.filter((r) => r.active) ?? [];

  const launchMutation = useMutation({
    mutationFn: () => tasksApi.create({ repo, goal, brainstorm }),
    onSuccess: async (data) => {
      toast({ title: "Build launched", description: data.task_id });
      await navigate({ to: "/tasks/$taskId", params: { taskId: data.task_id } });
    },
    onError: (e) => toast({ variant: "destructive", title: "Launch failed", description: String(e) }),
  });

  const canSubmit = repo && goal.length >= 10;

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Launch" description="Start a new build task" />
      <div className="flex-1 overflow-y-auto p-6">
        <div
          className="max-w-lg space-y-4 p-4 rounded-sm"
          style={{
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
          }}
        >
          <p
            className="font-mono font-bold tracking-wide"
            style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", letterSpacing: "var(--tracking-wide)" }}
          >
            NEW BUILD
          </p>

          <div className="space-y-1">
            <Label
              className="font-mono mb-1 block"
              style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
            >
              Repository
            </Label>
            <Select value={repo} onValueChange={setRepo}>
              <SelectTrigger
                className="font-mono rounded-sm h-8"
                style={{
                  fontSize: "var(--text-xs)",
                  backgroundColor: "var(--surface)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                }}
              >
                <SelectValue placeholder="select a repo…" />
              </SelectTrigger>
              <SelectContent
                style={{
                  backgroundColor: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                {activeRepos.map((r) => (
                  <SelectItem
                    key={r.full_name}
                    value={r.full_name}
                    className="font-mono"
                    style={{ fontSize: "var(--text-xs)" }}
                  >
                    {r.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label
              className="font-mono mb-1 block"
              style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
            >
              Goal
            </Label>
            <Textarea
              placeholder="Describe what you want built…"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="min-h-[100px]"
            />
            <p
              className="font-mono"
              style={{ fontSize: "var(--text-xs)", color: "var(--text-dim)" }}
            >
              {goal.length} chars (min 10)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="brainstorm"
              checked={brainstorm}
              onCheckedChange={(checked) => setBrainstorm(checked === true)}
            />
            <Label
              htmlFor="brainstorm"
              className="font-mono cursor-pointer"
              style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
            >
              Enable brainstorm stage
            </Label>
          </div>

          <Button
            className="w-full font-mono font-bold rounded-sm h-8"
            style={{
              fontSize: "var(--text-xs)",
              backgroundColor: canSubmit && !launchMutation.isPending ? "var(--accent)" : "var(--accent-dim)",
              color: "var(--bg, var(--background))",
              border: "none",
            }}
            onClick={() => launchMutation.mutate()}
            disabled={!canSubmit || launchMutation.isPending}
          >
            {launchMutation.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
            ) : null}
            ▶ LAUNCH
          </Button>
        </div>
      </div>
    </div>
  );
}
