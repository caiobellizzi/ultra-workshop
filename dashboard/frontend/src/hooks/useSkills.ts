import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { skills as skillsApi } from "@/lib/api";

export function useSkillStats() {
  return useQuery({
    queryKey: ["skills", "stats"],
    queryFn: () => skillsApi.stats(),
    refetchInterval: 30_000,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      skillsApi.create(name, content),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export function useSetSkillEnabled() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      skillsApi.setEnabled(name, enabled),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export function useSkillList() {
  return useQuery({
    queryKey: ["skills"],
    queryFn: () => skillsApi.list(),
  });
}

export function useSkill(name: string) {
  return useQuery({
    queryKey: ["skill", name],
    queryFn: () => skillsApi.get(name),
    enabled: !!name,
  });
}

export function useSaveSkill(name: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => skillsApi.put(name, content),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["skill", name] });
      void qc.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useSkillHistory(name: string) {
  return useQuery({
    queryKey: ["skill-history", name],
    queryFn: () => skillsApi.history(name),
    enabled: !!name,
  });
}

export function useRollbackSkill(name: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commit: string) => skillsApi.rollback(name, commit),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["skill", name] }),
  });
}
