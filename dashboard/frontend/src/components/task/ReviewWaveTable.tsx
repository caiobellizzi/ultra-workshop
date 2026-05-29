import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle, XCircle } from "lucide-react";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { CostPill } from "@/components/shared/CostPill";
import { Badge } from "@/components/ui/badge";
import type { WaveReport, MergeReport, ReviewFinding } from "@/types/task";
import { cn } from "@/lib/utils";

function FindingRow({ finding }: { finding: ReviewFinding }) {
  return (
    <div className="border-t px-4 py-2 text-sm space-y-1">
      <div className="flex items-center gap-2 flex-wrap">
        <SeverityBadge severity={finding.severity} />
        {finding.file && (
          <code className="text-xs text-muted-foreground">{finding.file}{finding.line ? `:${finding.line}` : ""}</code>
        )}
      </div>
      <p className="text-sm">{finding.problem}</p>
      {finding.required_fix && (
        <p className="text-xs text-muted-foreground italic">{finding.required_fix}</p>
      )}
    </div>
  );
}

function WaveRow({ report }: { report: WaveReport }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border rounded-md overflow-hidden">
      <button
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-muted/50 transition-colors text-left",
          report.passed ? "bg-green-50" : "bg-red-50",
        )}
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
        <span className="flex-1 font-medium">{report.role}</span>
        {report.passed ? (
          <CheckCircle className="h-4 w-4 text-green-500" />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" />
        )}
        <Badge variant="outline" className="text-xs">
          {report.findings.length} finding{report.findings.length !== 1 ? "s" : ""}
        </Badge>
        <CostPill cents={report.cost_cents} />
      </button>
      {open && report.findings.map((f, i) => <FindingRow key={i} finding={f} />)}
    </div>
  );
}

function MergeReportSection({ report }: { report: MergeReport }) {
  return (
    <div className="mt-4 space-y-2">
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-semibold">Merge Report</h4>
        {report.block_push ? (
          <Badge variant="destructive">Blocked</Badge>
        ) : (
          <Badge variant="success">Clear to merge</Badge>
        )}
      </div>
      {report.summary && <p className="text-sm text-muted-foreground">{report.summary}</p>}
      {report.auto_fixed.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">Auto-fixed:</p>
          <ul className="text-xs space-y-0.5 mt-1">
            {report.auto_fixed.map((f, i) => (
              <li key={i} className="text-muted-foreground">{f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

interface ReviewWaveTableProps {
  waveReports?: WaveReport[];
  mergeReport?: MergeReport;
}

export function ReviewWaveTable({ waveReports, mergeReport }: ReviewWaveTableProps) {
  if (!waveReports || waveReports.length === 0) {
    return <p className="text-sm text-muted-foreground">Review wave in progress…</p>;
  }
  return (
    <div className="space-y-2">
      {waveReports.map((r, i) => (
        <WaveRow key={i} report={r} />
      ))}
      {mergeReport && <MergeReportSection report={mergeReport} />}
    </div>
  );
}
