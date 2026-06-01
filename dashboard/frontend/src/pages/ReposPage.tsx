import { useState } from "react";
import { Loader2, ExternalLink } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
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

  const repos = data?.repos ?? [];

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Repos" description="Workshop repo registry" />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Add repo + sync row */}
        <div className="flex gap-2 max-w-md">
          <Input
            placeholder="owner/repo"
            value={newRepo}
            onChange={(e) => setNewRepo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addMutation.mutate(newRepo)}
          />
          {/* btn-primary: amber accent bg */}
          <button
            onClick={() => addMutation.mutate(newRepo)}
            disabled={!newRepo || addMutation.isPending}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-sm)",
              backgroundColor: "var(--accent)",
              color: "var(--background)",
              border: "1px solid var(--accent-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 12px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
              opacity: !newRepo || addMutation.isPending ? 0.5 : 1,
            }}
          >
            {addMutation.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              "+"
            )}
            Add Repo
          </button>
          {/* btn-secondary: surface bg, border */}
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-sm)",
              backgroundColor: "var(--surface)",
              color: "var(--text)",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 12px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
              opacity: syncMutation.isPending ? 0.5 : 1,
            }}
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              "↑"
            )}
            Sync GitHub
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2
              className="h-6 w-6 animate-spin"
              style={{ color: "var(--text-muted)" }}
            />
          </div>
        ) : repos.length === 0 ? (
          /* Empty state: dashed border box */
          <div
            style={{
              border: "1px dashed var(--border)",
              borderRadius: "var(--radius-sm)",
              padding: "48px 24px",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "var(--text-xs)",
                color: "var(--text-dim)",
              }}
            >
              -- no repos configured --
            </span>
          </div>
        ) : (
          /* Shared table pattern */
          <div
            style={{
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <table className="w-full" style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}>
              <thead>
                <tr style={{ backgroundColor: "var(--surface)", borderBottom: "1px solid var(--border)" }}>
                  <th
                    className="text-left"
                    style={{ padding: "8px 12px", color: "var(--text-dim)", fontWeight: "var(--font-medium)", letterSpacing: "var(--tracking-wide)", textTransform: "uppercase" }}
                  >
                    Repo
                  </th>
                  <th
                    className="text-left"
                    style={{ padding: "8px 12px", color: "var(--text-dim)", fontWeight: "var(--font-medium)", letterSpacing: "var(--tracking-wide)", textTransform: "uppercase" }}
                  >
                    Branch
                  </th>
                  <th
                    className="text-left"
                    style={{ padding: "8px 12px", color: "var(--text-dim)", fontWeight: "var(--font-medium)", letterSpacing: "var(--tracking-wide)", textTransform: "uppercase" }}
                  >
                    Status
                  </th>
                  <th
                    className="text-left"
                    style={{ padding: "8px 12px", color: "var(--text-dim)", fontWeight: "var(--font-medium)", letterSpacing: "var(--tracking-wide)", textTransform: "uppercase" }}
                  >
                    Last Used
                  </th>
                  <th style={{ padding: "8px 12px" }} />
                </tr>
              </thead>
              <tbody>
                {repos.map((repo) => (
                  <tr
                    key={repo.full_name}
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    <td style={{ padding: "8px 12px" }}>
                      <a
                        href={`https://github.com/${repo.full_name}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1"
                        style={{ color: "var(--accent)", textDecoration: "none" }}
                        onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
                        onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
                      >
                        {repo.full_name}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                    <td style={{ padding: "8px 12px" }}>
                      <span
                        className="font-mono"
                        style={{
                          fontSize: "var(--text-xs)", color: "var(--info)",
                          backgroundColor: "var(--info-bg)", border: "1px solid var(--info-border)",
                          borderRadius: "var(--radius-sm)", padding: "1px 6px",
                        }}
                      >
                        {repo.default_branch}
                      </span>
                    </td>
                    <td style={{ padding: "8px 12px" }}>
                      {/* Token-safe badge — no variant="success" */}
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "var(--text-xs)",
                          padding: "2px 6px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid",
                          ...(repo.active
                            ? {
                                color: "var(--success)",
                                backgroundColor: "var(--success-bg)",
                                borderColor: "var(--success-border)",
                              }
                            : {
                                color: "var(--text-muted)",
                                backgroundColor: "var(--surface-raised)",
                                borderColor: "var(--border)",
                              }),
                        }}
                      >
                        {repo.active ? "✓ active" : "○ inactive"}
                      </span>
                    </td>
                    <td style={{ padding: "8px 12px", color: "var(--text-muted)" }}>
                      {repo.last_used ? new Date(repo.last_used).toLocaleDateString() : "never"}
                    </td>
                    <td style={{ padding: "8px 12px" }}>
                      {/* Delete with AlertDialog confirmation */}
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <button
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "var(--text-xs)",
                              color: "var(--danger)",
                              backgroundColor: "transparent",
                              border: "1px solid var(--danger-border)",
                              borderRadius: "var(--radius-sm)",
                              padding: "2px 8px",
                              cursor: "pointer",
                            }}
                          >
                            delete
                          </button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Remove repo?</AlertDialogTitle>
                            <AlertDialogDescription>
                              {repo.full_name} will be removed from the workshop registry. Existing tasks referencing this repo are not affected.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => removeMutation.mutate(repo.full_name)}
                            >
                              Remove
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
