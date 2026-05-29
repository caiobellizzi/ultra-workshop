import { Badge } from "@/components/ui/badge";
import type { FindingSeverity } from "@/types/task";

const VARIANT_MAP: Record<FindingSeverity, "destructive" | "warning" | "info"> = {
  Critical: "destructive",
  Important: "warning",
  Minor: "info",
};

export function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  return <Badge variant={VARIANT_MAP[severity]}>{severity}</Badge>;
}
