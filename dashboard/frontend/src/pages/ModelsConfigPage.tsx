import { useState, useRef, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useModelsConfig, useSaveModelAliases } from "@/hooks/useConfig";
import { toast } from "@/hooks/use-toast";

export function ModelsConfigPage() {
  const { data, isLoading } = useModelsConfig();
  const saveMutation = useSaveModelAliases();
  const [routing, setRouting] = useState<Record<string, string>>({});
  const originalRef = useRef<Record<string, string>>({});
  const initializedRef = useRef(false);

  useEffect(() => {
    if (data && !initializedRef.current) {
      initializedRef.current = true;
      const initial = Object.fromEntries(data.routing.map((r) => [r.agent, r.alias]));
      setRouting(initial);
      originalRef.current = initial;
    }
  }, [data]);

  const isDirty = JSON.stringify(routing) !== JSON.stringify(originalRef.current);

  const handleSave = () => {
    saveMutation.mutate(routing, {
      onSuccess: () => {
        originalRef.current = routing;
        toast({ title: "Saved", description: "Model aliases updated. LiteLLM restart may be needed." });
      },
      onError: (err) => {
        toast({ variant: "destructive", title: "Save failed", description: String(err) });
      },
    });
  };

  const aliases = data?.aliases.map((a) => a.alias) ?? [];

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Models Config"
        description="Agent → model alias routing"
        actions={
          <div className="flex items-center gap-2">
            {isDirty && <Badge variant="warning">Unsaved changes</Badge>}
            <button
              onClick={handleSave}
              disabled={!isDirty || saveMutation.isPending}
              className="border border-[--border-strong] text-[--bg] bg-[--accent] font-bold font-mono text-xs px-3 py-1 rounded-[--radius-sm] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            >
              {saveMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Save
            </button>
          </div>
        }
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-[--text-muted]" />
          </div>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Agent → Alias Matrix</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full">
                  <thead className="bg-[--surface]">
                    <tr className="border-b border-[--border] text-left">
                      <th className="py-2 font-mono text-xs text-[--text-muted] w-1/3">Agent</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted] w-1/3">Current Alias</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Timeout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.routing.map((row) => (
                      <tr key={row.agent} className="border-b border-[--border] last:border-0">
                        <td className="py-2 font-mono text-xs text-[--text-m]">{row.agent}</td>
                        <td className="py-2">
                          <Select
                            value={routing[row.agent] ?? row.alias}
                            onValueChange={(v) => setRouting((prev) => ({ ...prev, [row.agent]: v }))}
                          >
                            <SelectTrigger className="h-8 w-48 font-mono text-xs border-[--border-s] text-[--text-m]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {aliases.map((alias) => (
                                <SelectItem key={alias} value={alias} className="font-mono text-xs text-[--info]">
                                  {alias}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="py-2 font-mono text-xs text-[--text-muted]">
                          {row.stage_timeout != null ? `${row.stage_timeout}s` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="font-mono text-xs text-[--text-muted] tracking-widest uppercase">Alias Definitions</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full">
                  <thead className="bg-[--surface]">
                    <tr className="border-b border-[--border] text-left">
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Alias</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Provider</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Model</th>
                      <th className="py-2 font-mono text-xs text-[--text-muted]">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.aliases.map((a) => (
                      <tr key={a.alias} className="border-b border-[--border] last:border-0">
                        <td className="py-2 font-mono text-xs text-[--text-m]">{a.alias}</td>
                        <td className="py-2 font-mono text-xs text-[--text-m]">{a.provider}</td>
                        <td className="py-2 font-mono text-xs text-[--info]">{a.model_id}</td>
                        <td className="py-2">
                          {a.reachable && (
                            <Badge
                              variant={
                                a.reachable === "green"
                                  ? "success"
                                  : a.reachable === "yellow"
                                  ? "warning"
                                  : "destructive"
                              }
                            >
                              {a.reachable}
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
