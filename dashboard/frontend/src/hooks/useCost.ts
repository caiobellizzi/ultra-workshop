import { useQuery } from "@tanstack/react-query";
import { cost as costApi } from "@/lib/api";

export function useCostSummary(from?: string, to?: string) {
  return useQuery({
    queryKey: ["cost", "summary", from, to],
    queryFn: () => costApi.summary({ from, to }),
  });
}

export function useCostTasks(from?: string, to?: string) {
  return useQuery({
    queryKey: ["cost", "tasks", from, to],
    queryFn: () => costApi.tasks({ from, to }),
  });
}

export function useCostTrends(from?: string, to?: string) {
  return useQuery({
    queryKey: ["cost", "trends", from, to],
    queryFn: () => costApi.trends({ from, to }),
  });
}

export function useCostRoles() {
  return useQuery({
    queryKey: ["cost", "roles"],
    queryFn: () => costApi.roles(),
  });
}
