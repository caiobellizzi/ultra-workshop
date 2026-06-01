import { useState, lazy, Suspense } from "react";
import { useParams } from "@tanstack/react-router";
import { Loader2, Save, RotateCcw, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSkill, useSaveSkill } from "@/hooks/useSkills";
import { toast } from "@/hooks/use-toast";
import { useTheme } from "@/components/ThemeProvider";

// Monaco loaded lazily to avoid large bundle on other pages
const MonacoEditor = lazy(() =>
  import("@monaco-editor/react").then((m) => ({ default: m.default })),
);

const OUTPUT_SCHEMA_SECTION = "## Output Schema";

export function SkillEditorPage() {
  const params = useParams({ strict: false });
  const skillName = (params as { skillName?: string }).skillName ?? "";
  const { data, isLoading } = useSkill(skillName);
  const saveMutation = useSaveSkill(skillName);

  const { theme: currentTheme } = useTheme();
  const [content, setContent] = useState<string | null>(null);
  const [schemaWarning, setSchemaWarning] = useState(false);
  const [tab, setTab] = useState<"skill" | "config" | "hooks">("skill");

  const siblings = [
    { key: "config" as const, label: "config.yml", value: data?.config_yml, lang: "yaml" },
    { key: "hooks" as const, label: "hooks.yml", value: data?.hooks_yml, lang: "yaml" },
  ].filter((s) => s.value != null);
  const activeSibling = siblings.find((s) => s.key === tab);

  if (data && content === null) {
    setContent(data.content);
  }

  const originalContent = data?.content ?? "";
  const isDirty = content !== null && content !== originalContent;

  const checkSchemaChange = (newContent: string) => {
    const origSchema = originalContent.includes(OUTPUT_SCHEMA_SECTION)
      ? originalContent.slice(originalContent.indexOf(OUTPUT_SCHEMA_SECTION))
      : "";
    const newSchema = newContent.includes(OUTPUT_SCHEMA_SECTION)
      ? newContent.slice(newContent.indexOf(OUTPUT_SCHEMA_SECTION))
      : "";
    setSchemaWarning(origSchema !== newSchema);
  };

  const handleChange = (val?: string) => {
    if (val === undefined) return;
    setContent(val);
    checkSchemaChange(val);
  };

  const handleSave = () => {
    if (content === null) return;
    saveMutation.mutate(content, {
      onSuccess: () => toast({ title: "Saved", description: `${skillName} updated` }),
      onError: (e) => toast({ variant: "destructive", title: "Save failed", description: String(e) }),
    });
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title={skillName}
        description={data?.meta.description}
        actions={
          <div className="flex items-center gap-2">
            {isDirty && <Badge variant="warning">Unsaved</Badge>}
            {isDirty && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setContent(originalContent);
                  setSchemaWarning(false);
                }}
              >
                <RotateCcw className="h-4 w-4" />
                Discard
              </Button>
            )}
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!isDirty || saveMutation.isPending}
              className="bg-[--accent] text-[--bg] font-bold font-mono text-xs"
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save
            </Button>
          </div>
        }
      />

      {schemaWarning && (
        <div className="flex items-center gap-2 bg-[--warn-bg] border border-[--warn-bd] px-4 py-2 text-[--warning] font-mono text-xs">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Modifying the Output Schema may break the pipeline stage that consumes this skill&apos;s output.
          Verify all callers.
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="flex-1 overflow-hidden flex flex-col">
          {siblings.length > 0 && (
            <div className="flex items-center gap-1 px-4 py-1.5 border-b border-[--border]">
              {[{ key: "skill" as const, label: "SKILL.md" }, ...siblings].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className="font-mono text-xs px-2.5 py-1 rounded-sm"
                  style={{
                    cursor: "pointer",
                    backgroundColor: tab === t.key ? "var(--accent-bg)" : "transparent",
                    border: `1px solid ${tab === t.key ? "var(--accent-border)" : "transparent"}`,
                    color: tab === t.key ? "var(--accent)" : "var(--text-muted)",
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}
          <div className="flex-1 overflow-hidden">
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              }
            >
              {tab !== "skill" && activeSibling ? (
                <MonacoEditor
                  height="100%"
                  language={activeSibling.lang}
                  value={activeSibling.value ?? ""}
                  options={{
                    minimap: { enabled: false },
                    wordWrap: "on",
                    lineNumbers: "on",
                    fontSize: 13,
                    scrollBeyondLastLine: false,
                    readOnly: true,
                  }}
                  theme={currentTheme === "dark" ? "vs-dark" : "vs"}
                />
              ) : (
                <MonacoEditor
                  height="100%"
                  language="markdown"
                  value={content ?? ""}
                  onChange={handleChange}
                  options={{
                    minimap: { enabled: false },
                    wordWrap: "on",
                    lineNumbers: "on",
                    fontSize: 13,
                    scrollBeyondLastLine: false,
                  }}
                  theme={currentTheme === "dark" ? "vs-dark" : "vs"}
                />
              )}
            </Suspense>
          </div>
        </div>
      )}
    </div>
  );
}
