import { useState, useRef } from "react";
import { Loader2, Save } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useModelsConfig, useSaveModelAliases } from "@/hooks/useConfig";
import { toast } from "@/hooks/use-toast";

export function ModelsConfigPage() {
  const { data, isLoading } = useModelsConfig();
  const saveMutation = useSaveModelAliases();
  const [routing, setRouting] = useState<Record<string, string>>({});
  const originalRef = useRef<Record<string, string>>({});

  // Initialize local state from fetched data
  if (data && Object.keys(routing).length === 0) {
    const initial = Object.fromEntries(data.routing.map((r) => [r.agent, r.alias]));
    setRouting(initial);
    originalRef.current = initial;
  }

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
            <Button size="sm" onClick={handleSave} disabled={!isDirty || saveMutation.isPending}>
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save
            </Button>
          </div>
        }
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Agent → Alias Matrix</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium text-muted-foreground w-1/3">Agent</th>
                      <th className="pb-2 font-medium text-muted-foreground w-1/3">Current Alias</th>
                      <th className="pb-2 font-medium text-muted-foreground">Timeout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.routing.map((row) => (
                      <tr key={row.agent} className="border-b last:border-0">
                        <td className="py-2 font-mono text-xs">{row.agent}</td>
                        <td className="py-2">
                          <Select
                            value={routing[row.agent] ?? row.alias}
                            onValueChange={(v) => setRouting((prev) => ({ ...prev, [row.agent]: v }))}
                          >
                            <SelectTrigger className="h-8 w-48 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {aliases.map((alias) => (
                                <SelectItem key={alias} value={alias} className="text-xs">
                                  {alias}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="py-2 text-xs text-muted-foreground">
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
                <CardTitle className="text-sm">Alias Definitions</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium text-muted-foreground">Alias</th>
                      <th className="pb-2 font-medium text-muted-foreground">Provider</th>
                      <th className="pb-2 font-medium text-muted-foreground">Model</th>
                      <th className="pb-2 font-medium text-muted-foreground">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.aliases.map((a) => (
                      <tr key={a.alias} className="border-b last:border-0">
                        <td className="py-2 font-mono text-xs">{a.alias}</td>
                        <td className="py-2 text-xs">{a.provider}</td>
                        <td className="py-2 text-xs text-muted-foreground">{a.model_id}</td>
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
