import { useState, lazy, Suspense } from "react";
import { useParams } from "@tanstack/react-router";
import { Loader2, Save, RotateCcw, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSkill, useSaveSkill } from "@/hooks/useSkills";
import { toast } from "@/hooks/use-toast";

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

  const [content, setContent] = useState<string | null>(null);
  const [schemaWarning, setSchemaWarning] = useState(false);

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
            <Button size="sm" onClick={handleSave} disabled={!isDirty || saveMutation.isPending}>
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
        <div className="flex items-center gap-2 bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-700">
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
        <div className="flex-1 overflow-hidden">
          <Suspense
            fallback={
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            }
          >
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
              theme="vs-light"
            />
          </Suspense>
        </div>
      )}
    </div>
  );
}
