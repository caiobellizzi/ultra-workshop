import { useRef, useEffect, useState, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArrowDown, WifiOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useTaskLogStream } from "@/lib/useSSE";
import type { LogLine } from "@/lib/useSSE";
import { cn } from "@/lib/utils";

function LogLineRow({ line }: { line: LogLine }) {
  const isError = String(line.event).includes("error") || String(line.event).includes("fail");
  const isWarn = String(line.event).includes("warn") || String(line.event).includes("timeout");
  return (
    <div className={cn(
      "flex items-start gap-2 px-2 py-0.5 font-mono text-xs",
      isError && "text-red-500",
      isWarn && "text-amber-500",
      !isError && !isWarn && "text-foreground",
    )}>
      <span className="text-muted-foreground shrink-0 tabular-nums">
        {new Date(line.ts).toLocaleTimeString()}
      </span>
      <span className="text-blue-500 shrink-0">{line.event}</span>
      <span className="break-all">
        {Object.entries(line)
          .filter(([k]) => k !== "ts" && k !== "event")
          .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
          .join(" ")}
      </span>
    </div>
  );
}

export function LogStream({ taskId }: { taskId: string }) {
  const { lines, status, reconnect } = useTaskLogStream(taskId, true);
  const [filter, setFilter] = useState("");
  const [userScrolled, setUserScrolled] = useState(false);
  const parentRef = useRef<HTMLDivElement>(null);

  const filtered = filter
    ? lines.filter((l) => JSON.stringify(l).toLowerCase().includes(filter.toLowerCase()))
    : lines;

  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 22,
    overscan: 20,
  });

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    if (!userScrolled && filtered.length > 0) {
      rowVirtualizer.scrollToIndex(filtered.length - 1, { align: "end" });
    }
  }, [filtered.length, userScrolled, rowVirtualizer]);

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setUserScrolled(!atBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    rowVirtualizer.scrollToIndex(filtered.length - 1, { align: "end" });
    setUserScrolled(false);
  }, [rowVirtualizer, filtered.length]);

  return (
    <div className="flex flex-col h-64 border rounded-md overflow-hidden">
      <div className="flex items-center gap-2 px-2 py-1 border-b bg-muted/30">
        <span className="text-xs font-medium text-muted-foreground">Live Logs</span>
        {status === "error" && (
          <span className="flex items-center gap-1 text-xs text-destructive">
            <WifiOff className="h-3 w-3" />
            Disconnected
            <Button size="sm" variant="ghost" className="h-5 px-1 text-xs" onClick={reconnect}>
              <RefreshCw className="h-3 w-3" />
            </Button>
          </span>
        )}
        {status === "connecting" && (
          <span className="text-xs text-muted-foreground animate-pulse">Connecting…</span>
        )}
        <div className="flex-1" />
        <Input
          className="h-6 w-48 text-xs"
          placeholder="Filter…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div
        ref={parentRef}
        className="flex-1 overflow-y-auto bg-background"
        onScroll={handleScroll}
      >
        <div
          style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: "relative" }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => (
            <div
              key={virtualRow.index}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <LogLineRow line={filtered[virtualRow.index]} />
            </div>
          ))}
        </div>
      </div>

      {userScrolled && (
        <button
          className="absolute bottom-2 right-2 flex items-center gap-1 rounded-full bg-primary px-2 py-1 text-xs text-primary-foreground shadow"
          onClick={scrollToBottom}
        >
          <ArrowDown className="h-3 w-3" />
          Jump to bottom
        </button>
      )}
    </div>
  );
}
