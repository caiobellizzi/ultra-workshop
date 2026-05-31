// Generic SSE hook with ring-buffer cap and exponential backoff reconnection.
import { useEffect, useRef, useState, useCallback } from "react";

export type SSEStatus = "connecting" | "open" | "error" | "closed";

export interface SSEOptions {
  /** Maximum number of lines to keep in the ring buffer. Default 2000. */
  cap?: number;
  /** Enable/disable the connection. Default true. */
  enabled?: boolean;
  /** Initial backoff in ms. Default 1000. */
  initialBackoff?: number;
  /** Max backoff in ms. Default 30000. */
  maxBackoff?: number;
}

export interface SSEState<T> {
  lines: T[];
  status: SSEStatus;
  reconnect: () => void;
  clear: () => void;
}

export function useSSE<T = unknown>(
  url: string,
  onMessage?: (data: T) => void,
  options: SSEOptions & { namedEvents?: string[] } = {},
): SSEState<T> {
  const {
    cap = 2000,
    enabled = true,
    initialBackoff = 1000,
    maxBackoff = 30_000,
    namedEvents = ["log", "state", "progress"],
  } = options;

  const [lines, setLines] = useState<T[]>([]);
  const [status, setStatus] = useState<SSEStatus>("closed");
  const esRef = useRef<EventSource | null>(null);
  const backoffRef = useRef(initialBackoff);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const connect = useCallback(() => {
    if (!enabledRef.current) return;
    if (esRef.current) {
      esRef.current.close();
    }
    setStatus("connecting");
    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    es.onopen = () => {
      setStatus("open");
      backoffRef.current = initialBackoff; // reset on success
    };

    es.onmessage = (e: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(e.data) as T;
        if (onMessage) onMessage(parsed);
        setLines((prev) => {
          const next = prev.length >= cap ? prev.slice(-(cap - 1)) : prev;
          return [...next, parsed];
        });
      } catch {
        // Ignore parse errors for non-JSON SSE messages
      }
    };

    const handleNamedEvent = (e: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(e.data) as T;
        if (onMessage) onMessage(parsed);
        setLines((prev) => {
          const next = prev.length >= cap ? prev.slice(-(cap - 1)) : prev;
          return [...next, parsed];
        });
      } catch {
        // Ignore parse errors for non-JSON SSE messages
      }
    };

    namedEvents.forEach((name) => {
      es.addEventListener(name, handleNamedEvent);
    });

    es.onerror = () => {
      setStatus("error");
      es.close();
      esRef.current = null;
      if (!enabledRef.current) return;
      // Exponential backoff
      const delay = Math.min(backoffRef.current, maxBackoff);
      backoffRef.current = Math.min(backoffRef.current * 2, maxBackoff);
      retryTimerRef.current = setTimeout(() => {
        if (enabledRef.current) connect();
      }, delay);
    };
  }, [url, cap, initialBackoff, maxBackoff, onMessage]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      enabledRef.current = false;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      setStatus("closed");
    };
    // connect is stable (useCallback with fixed deps), url + enabled trigger re-connection
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, enabled]);

  const reconnect = useCallback(() => {
    backoffRef.current = initialBackoff;
    connect();
  }, [connect, initialBackoff]);

  const clear = useCallback(() => setLines([]), []);

  return { lines, status, reconnect, clear };
}

// Specialised hook for task log stream
export interface LogLine {
  ts: string;
  event: string;
  [key: string]: unknown;
}

export function useTaskLogStream(
  taskId: string,
  enabled = true,
): SSEState<LogLine> {
  return useSSE<LogLine>(
    `/api/sse/tasks/${taskId}/logs`,
    undefined,
    { enabled, cap: 2000 },
  );
}

export function useTaskEventStream(
  taskId: string,
  enabled = true,
): SSEState<LogLine> {
  return useSSE<LogLine>(
    `/api/sse/tasks/${taskId}/events`,
    undefined,
    { enabled, cap: 2000 },
  );
}
