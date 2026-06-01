import { useQuery, useMutation } from "@tanstack/react-query";
import { cost as costApi, tasks as tasksApi } from "@/lib/api";

export function useModelMix() {
  return useQuery({
    queryKey: ["tasks", "model-mix"],
    queryFn: () => tasksApi.modelMix(),
    refetchInterval: 10_000,
  });
}

export function useCostEstimate() {
  return useMutation({
    mutationFn: (repo: string) => costApi.estimate(repo),
  });
}

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
