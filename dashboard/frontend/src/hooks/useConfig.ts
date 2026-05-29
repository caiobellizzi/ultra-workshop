import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { config as configApi } from "@/lib/api";
import type { ReviewerEntry, PoliciesConfig } from "@/types/config";

export function useModelsConfig() {
  return useQuery({
    queryKey: ["config", "models"],
    queryFn: () => configApi.getModels(),
  });
}

export function useSaveModelAliases() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (routing: Record<string, string>) => configApi.putModelAliases(routing),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["config", "models"] }),
  });
}

export function useReviewersConfig() {
  return useQuery({
    queryKey: ["config", "reviewers"],
    queryFn: () => configApi.getReviewers(),
  });
}

export function useSaveReviewers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewers: ReviewerEntry[]) => configApi.putReviewers(reviewers),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["config", "reviewers"] }),
  });
}

export function usePoliciesConfig() {
  return useQuery({
    queryKey: ["config", "policies"],
    queryFn: () => configApi.getPolicies(),
  });
}

export function useSavePolicies() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (policies: PoliciesConfig) => configApi.putPolicies(policies),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["config", "policies"] }),
  });
}

export function useCronJobs() {
  return useQuery({
    queryKey: ["cron"],
    queryFn: () => configApi.getCron(),
  });
}
