import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Loader2, Rocket } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
        <Card className="max-w-lg">
          <CardHeader>
            <CardTitle className="text-base">New Build</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Repository</Label>
              <Select value={repo} onValueChange={setRepo}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a repo…" />
                </SelectTrigger>
                <SelectContent>
                  {activeRepos.map((r) => (
                    <SelectItem key={r.full_name} value={r.full_name}>
                      {r.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Goal</Label>
              <textarea
                className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[100px] resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Describe what you want built…"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">{goal.length} chars (min 10)</p>
            </div>

            <div className="flex items-center gap-2">
              <input
                id="brainstorm"
                type="checkbox"
                checked={brainstorm}
                onChange={(e) => setBrainstorm(e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="brainstorm">Enable brainstorm stage</Label>
            </div>

            <Button
              className="w-full"
              onClick={() => launchMutation.mutate()}
              disabled={!canSubmit || launchMutation.isPending}
            >
              {launchMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Rocket className="h-4 w-4" />
              )}
              Launch Build
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
