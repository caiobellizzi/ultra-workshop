import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Diff } from "@/types/task";
import { cn } from "@/lib/utils";

function DiffLine({ line }: { line: string }) {
  const isAdded = line.startsWith("+");
  const isRemoved = line.startsWith("-");
  const isHeader = line.startsWith("@@");
  return (
    <div
      className={cn(
        "font-mono text-xs whitespace-pre px-2 py-0.5 leading-5",
        isAdded && "bg-green-50 text-green-800",
        isRemoved && "bg-red-50 text-red-800",
        isHeader && "bg-blue-50 text-blue-700",
        !isAdded && !isRemoved && !isHeader && "text-muted-foreground",
      )}
    >
      {line}
    </div>
  );
}

function FileChangeRow({ path, diff, additions, deletions }: {
  path: string;
  diff: string;
  additions: number;
  deletions: number;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border rounded-md overflow-hidden">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-sm bg-muted/50 hover:bg-muted transition-colors text-left"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
        <code className="flex-1 truncate">{path}</code>
        <span className="text-green-600 text-xs">+{additions}</span>
        <span className="text-red-600 text-xs ml-1">-{deletions}</span>
      </button>
      {open && (
        <ScrollArea className="max-h-96">
          <div className="text-xs">
            {diff.split("\n").map((line, i) => (
              <DiffLine key={i} line={line} />
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}

export function DiffViewer({ diff }: { diff: Diff }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <Badge variant="outline">{diff.branch}</Badge>
        <span className="flex items-center gap-1 text-sm">
          {diff.build_passed ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : (
            <XCircle className="h-4 w-4 text-destructive" />
          )}
          Build
        </span>
        <span className="flex items-center gap-1 text-sm">
          {diff.test_passed ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : (
            <XCircle className="h-4 w-4 text-destructive" />
          )}
          Tests
        </span>
      </div>

      {diff.summary && <p className="text-sm text-muted-foreground">{diff.summary}</p>}

      <div className="space-y-2">
        {diff.changes.map((fc) => (
          <FileChangeRow key={fc.path} {...fc} />
        ))}
      </div>

      {diff.output_tail && (
        <details className="mt-2">
          <summary className="text-sm text-muted-foreground cursor-pointer">Build output</summary>
          <ScrollArea className="mt-1 max-h-40">
            <pre className="text-xs bg-muted p-2 rounded-md">{diff.output_tail}</pre>
          </ScrollArea>
        </details>
      )}
    </div>
  );
}
