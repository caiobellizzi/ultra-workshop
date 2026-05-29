import { cn } from "@/lib/utils";

export function CostPill({ cents, className }: { cents: number; className?: string }) {
  const formatted =
    cents < 1 ? "$0.00" : cents < 100 ? `$${(cents / 100).toFixed(3)}` : `$${(cents / 100).toFixed(2)}`;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-mono text-muted-foreground",
        className,
      )}
    >
      {formatted}
    </span>
  );
}
