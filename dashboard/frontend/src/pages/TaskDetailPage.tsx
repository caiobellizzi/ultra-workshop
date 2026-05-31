import { useState, useEffect } from "react";
import { useParams } from "@tanstack/react-router";
import { ExternalLink } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { PageHeader } from "@/components/layout/PageHeader";
import { PipelineGraph } from "@/components/task/PipelineGraph";
import { StageOutputPane } from "@/components/task/StageOutputPane";
import { LogStream } from "@/components/task/LogStream";
import { HITLCard } from "@/components/hitl/HITLCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { CostPill } from "@/components/shared/CostPill";
import { useTask } from "@/hooks/useTasks";
import { formatDuration } from "@/lib/utils";
import type { ReviewFinding, FindingSeverity } from "@/types/task";

// ──────────────────────────────────────────────────────────────
// Responsive breakpoint hook (< 1200px → slide-over mode)
// ──────────────────────────────────────────────────────────────
function useNarrow(breakpoint = 1200): boolean {
  const [narrow, setNarrow] = useState(() => window.innerWidth < breakpoint);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    const handler = (e: MediaQueryListEvent) => setNarrow(e.matches);
    setNarrow(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [breakpoint]);
  return narrow;
}

// ──────────────────────────────────────────────────────────────
// Review findings right panel content
// ──────────────────────────────────────────────────────────────
const FINDING_BORDER: Record<FindingSeverity, string> = {
  Critical:  "var(--danger)",
  Important: "var(--warning)",
  Minor:     "var(--text-d)",
};

function FindingItem({ finding }: { finding: ReviewFinding }) {
  const borderColor = FINDING_BORDER[finding.severity] ?? "var(--border)";
  return (
    <div
      style={{
        borderLeft: `2px solid ${borderColor}`,
        paddingLeft: "8px",
        paddingTop: "6px",
        paddingBottom: "6px",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: borderColor,
          letterSpacing: "var(--tracking-wide)",
          textTransform: "uppercase",
          marginBottom: "2px",
        }}
      >
        {finding.severity}
        {finding.file && (
          <span style={{ color: "var(--info)", marginLeft: "8px", textTransform: "none", letterSpacing: "normal" }}>
            {finding.file}{finding.line ? `:${finding.line}` : ""}
          </span>
        )}
      </div>
      <p style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", color: "var(--text)", margin: 0 }}>
        {finding.problem}
      </p>
      {finding.required_fix && (
        <p style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
          fix: {finding.required_fix}
        </p>
      )}
    </div>
  );
}

interface ReviewPanelContentProps {
  findings: ReviewFinding[];
  pushBlocked: boolean;
  blockSummary?: string;
}

function ReviewPanelContent({ findings, pushBlocked, blockSummary }: ReviewPanelContentProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", padding: "16px" }}>
      {/* Push-blocked banner */}
      {pushBlocked && (
        <div
          style={{
            backgroundColor: "var(--danger-bg)",
            border: "1px solid var(--danger-bd)",
            borderRadius: "var(--radius-sm)",
            color: "var(--danger)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-xs)",
            letterSpacing: "var(--tracking-wide)",
            padding: "6px 10px",
            marginBottom: "8px",
          }}
        >
          ✗ PUSH BLOCKED{blockSummary ? ` — ${blockSummary}` : ""}
        </div>
      )}

      {/* Panel header */}
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--text-d)",
          letterSpacing: "var(--tracking-wide)",
          textTransform: "uppercase",
          paddingBottom: "8px",
          borderBottom: "1px solid var(--border)",
          marginBottom: "8px",
        }}
      >
        Review Findings ({findings.length})
      </div>

      {findings.length === 0 ? (
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-sm)",
            color: "var(--text-d)",
            textAlign: "center",
            padding: "32px 0",
          }}
        >
          --no findings--
        </p>
      ) : (
        findings.map((f, i) => <FindingItem key={i} finding={f} />)
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────
// Metadata table row
// ──────────────────────────────────────────────────────────────
function MetaRow({ label, children, dim = false }: { label: string; children: React.ReactNode; dim?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "6px 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--text-d)",
          letterSpacing: "var(--tracking-wide)",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-sm)",
          color: dim ? "var(--text-muted)" : "var(--text)",
        }}
      >
        {children}
      </span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────
// Main page
// ──────────────────────────────────────────────────────────────
export function TaskDetailPage() {
  const params = useParams({ strict: false });
  const taskId = (params as { taskId?: string }).taskId ?? "";
  const { data: task, isLoading, error } = useTask(taskId);
  const isNarrow = useNarrow(1200);
  const [sheetOpen, setSheetOpen] = useState(false);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: "8px",
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-sm)",
          color: "var(--text-muted)",
        }}
      >
        <span className="animate-pulse">◑</span>
        <span>loading…</span>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
        }}
      >
        <div
          style={{
            backgroundColor: "var(--danger-bg)",
            border: "1px solid var(--danger-bd)",
            borderRadius: "var(--radius-sm)",
            color: "var(--danger)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-sm)",
            padding: "8px 16px",
          }}
        >
          ✗ task not found or failed to load
        </div>
      </div>
    );
  }

  const hitlPayload =
    task.approval_payload ?? (task.timeout_payload as typeof task.approval_payload);
  const isHitl =
    task.status !== "running" &&
    task.status !== "pushed" &&
    task.status !== "stopped" &&
    hitlPayload != null;

  // Collect all review findings for the right panel
  const allFindings: ReviewFinding[] = [];
  if (task.stages.wave_reports) {
    for (const wave of task.stages.wave_reports) {
      allFindings.push(...wave.findings);
    }
  }
  const mergeReport = task.stages.merge_report;
  const pushBlocked = mergeReport?.block_push ?? false;
  const findingCount = allFindings.length;
  const hasReviewPanel = findingCount > 0 || pushBlocked || isHitl;

  // Right panel content (shared between inline and sheet)
  const rightPanelContent = (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {isHitl && hitlPayload && (
        <div
          style={{
            borderBottom: "1px solid var(--border)",
            padding: "16px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xs)",
              color: "var(--warning)",
              letterSpacing: "var(--tracking-wide)",
              textTransform: "uppercase",
              marginBottom: "12px",
            }}
          >
            ⌛ ACTION REQUIRED
          </div>
          <HITLCard taskId={taskId} payload={hitlPayload} />
        </div>
      )}

      {(findingCount > 0 || pushBlocked) && (
        <div style={{ flex: 1, overflowY: "auto" }}>
          <ReviewPanelContent
            findings={allFindings}
            pushBlocked={pushBlocked}
            blockSummary={mergeReport?.summary}
          />
        </div>
      )}
    </div>
  );

  // Button shown in topbar on narrow viewports
  const reviewTriggerLabel =
    findingCount > 0
      ? `Review (${findingCount} finding${findingCount !== 1 ? "s" : ""})`
      : isHitl
      ? "Action Required"
      : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Top bar */}
      <PageHeader
        title={task.goal.slice(0, 60)}
        description={
          // Breadcrumb: font-mono text-xs text-[--text-d]
          `${task.task_id}`
        }
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <StatusBadge status={task.status} />
            {/* Narrow viewport: sheet trigger */}
            {isNarrow && hasReviewPanel && reviewTriggerLabel && (
              <button
                onClick={() => setSheetOpen(true)}
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--text-xs)",
                  color: isHitl ? "var(--warning)" : "var(--info)",
                  backgroundColor: isHitl ? "var(--warning-bg)" : "var(--info-bg)",
                  border: `1px solid ${isHitl ? "var(--warning-border)" : "var(--info-bd)"}`,
                  borderRadius: "var(--radius-sm)",
                  padding: "2px 8px",
                  cursor: "pointer",
                }}
              >
                {reviewTriggerLabel}
              </button>
            )}
          </div>
        }
      />

      {/* 3-panel body */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* ── Left panel: 220px fixed ── */}
        <aside
          style={{
            width: "220px",
            flexShrink: 0,
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
            backgroundColor: "var(--surface)",
          }}
        >
          {/* Pipeline stage progress */}
          <div
            style={{
              padding: "16px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <PipelineGraph task={task} />
          </div>

          {/* Metadata table */}
          <div style={{ padding: "8px 16px", flex: 1 }}>
            {task.repo_full_name && (
              <MetaRow label="Repo">
                <a
                  href={`https://github.com/${task.repo_full_name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: "var(--info)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--text-sm)",
                    textDecoration: "none",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <ExternalLink style={{ width: "10px", height: "10px" }} />
                  {task.repo_full_name.split("/")[1] ?? task.repo_full_name}
                </a>
              </MetaRow>
            )}
            {task.default_branch && (
              <MetaRow label="Branch" dim>
                {task.default_branch}
              </MetaRow>
            )}
            <MetaRow label="Elapsed" dim>
              {formatDuration(task.created_at)}
            </MetaRow>
            <MetaRow label="Cost">
              <CostPill cents={task.cost_cents_so_far} />
            </MetaRow>
            {/* Attempt counts per stage */}
            {Object.entries(task.attempts)
              .filter(([, v]) => v > 0)
              .map(([stage, count]) => (
                <MetaRow key={stage} label={stage} dim>
                  {count}x
                </MetaRow>
              ))}
          </div>
        </aside>

        {/* ── Main panel: flex-1 ── */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Stage output (tabs) */}
          <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
            <StageOutputPane task={task} />
          </div>

          {/* Log stream */}
          <div
            style={{
              borderTop: "1px solid var(--border)",
              padding: "16px",
              height: "240px",
              flexShrink: 0,
            }}
          >
            <LogStream taskId={taskId} />
          </div>
        </div>

        {/* ── Right panel: inline (wide viewport only) ── */}
        {!isNarrow && hasReviewPanel && (
          <aside
            style={{
              width: "320px",
              flexShrink: 0,
              borderLeft: "1px solid var(--border)",
              overflowY: "auto",
              backgroundColor: "var(--surface)",
            }}
          >
            {rightPanelContent}
          </aside>
        )}
      </div>

      {/* ── Sheet slide-over (narrow viewport) ── */}
      {isNarrow && hasReviewPanel && (
        <Dialog.Root open={sheetOpen} onOpenChange={setSheetOpen}>
          <Dialog.Portal>
            {/* Overlay */}
            <Dialog.Overlay
              style={{
                position: "fixed",
                inset: 0,
                backgroundColor: "rgba(0,0,0,0.7)",
                zIndex: 50,
              }}
            />
            {/* Slide-over panel from right */}
            <Dialog.Content
              style={{
                position: "fixed",
                top: 0,
                right: 0,
                bottom: 0,
                width: "360px",
                maxWidth: "90vw",
                backgroundColor: "var(--surface)",
                borderLeft: "1px solid var(--border)",
                zIndex: 51,
                display: "flex",
                flexDirection: "column",
                overflowY: "auto",
              }}
            >
              {/* Sheet header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--border)",
                  flexShrink: 0,
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--text-xs)",
                    color: "var(--text-d)",
                    letterSpacing: "var(--tracking-wide)",
                    textTransform: "uppercase",
                  }}
                >
                  {reviewTriggerLabel}
                </span>
                <Dialog.Close asChild>
                  <button
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--text-sm)",
                      color: "var(--text-muted)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: "2px 6px",
                    }}
                    aria-label="Close"
                  >
                    ✗
                  </button>
                </Dialog.Close>
              </div>

              {/* Sheet body */}
              <div style={{ flex: 1, overflowY: "auto" }}>
                {rightPanelContent}
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </div>
  );
}
