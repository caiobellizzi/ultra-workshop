import { useQuery } from "@tanstack/react-query";
import { hitl as hitlApi } from "@/lib/api";

export function useHITLQueue() {
  return useQuery({
    queryKey: ["hitl"],
    queryFn: () => hitlApi.list(),
    refetchInterval: 3_000,
  });
}
