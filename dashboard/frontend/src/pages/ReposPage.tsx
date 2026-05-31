import { useState } from "react";
import { Loader2, Plus, Trash2, ExternalLink, Github } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { repos as reposApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

export function ReposPage() {
  const qc = useQueryClient();
  const [newRepo, setNewRepo] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["repos"],
    queryFn: () => reposApi.list(),
  });

  const addMutation = useMutation({
    mutationFn: (repo: string) => reposApi.add(repo),
    onSuccess: () => {
      setNewRepo("");
      void qc.invalidateQueries({ queryKey: ["repos"] });
      toast({ title: "Repo added" });
    },
    onError: (e) => toast({ variant: "destructive", title: "Failed", description: String(e) }),
  });

  const removeMutation = useMutation({
    mutationFn: (fullName: string) => reposApi.remove(fullName),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["repos"] }),
  });

  const syncMutation = useMutation({
    mutationFn: () => reposApi.syncGithub(),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: ["repos"] });
      toast({
        title: "GitHub sync complete",
        description: `${result.imported} repos imported, ${result.skipped} already registered`,
      });
    },
    onError: (e) => toast({ variant: "destructive", title: "Sync failed", description: String(e) }),
  });

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Repos" description="Workshop repo registry" />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <div className="flex gap-2 max-w-md">
          <Input
            placeholder="owner/repo"
            value={newRepo}
            onChange={(e) => setNewRepo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addMutation.mutate(newRepo)}
          />
          <Button
            onClick={() => addMutation.mutate(newRepo)}
            disabled={!newRepo || addMutation.isPending}
          >
            {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add
          </Button>
          <Button
            variant="outline"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Github className="h-4 w-4" />
            )}
            Sync GitHub
          </Button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium text-muted-foreground">Repo</th>
                    <th className="p-3 font-medium text-muted-foreground">Branch</th>
                    <th className="p-3 font-medium text-muted-foreground">Status</th>
                    <th className="p-3 font-medium text-muted-foreground">Last Used</th>
                    <th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data?.repos.map((repo) => (
                    <tr key={repo.full_name} className="border-b last:border-0">
                      <td className="p-3">
                        <a
                          href={`https://github.com/${repo.full_name}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-primary hover:underline font-mono text-xs"
                        >
                          {repo.full_name}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </td>
                      <td className="p-3 text-xs">{repo.default_branch}</td>
                      <td className="p-3">
                        <Badge variant={repo.active ? "success" : "secondary"}>
                          {repo.active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="p-3 text-xs text-muted-foreground">
                        {repo.last_used ? new Date(repo.last_used).toLocaleDateString() : "Never"}
                      </td>
                      <td className="p-3">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0"
                          onClick={() => removeMutation.mutate(repo.full_name)}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
