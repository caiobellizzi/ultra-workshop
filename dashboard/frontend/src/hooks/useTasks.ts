import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasks as tasksApi } from "@/lib/api";

export function useTaskList(status?: string) {
  return useQuery({
    queryKey: ["tasks", { status }],
    queryFn: () => tasksApi.list({ status, limit: 100 }),
    refetchInterval: 5_000,
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => tasksApi.get(id),
    refetchInterval: 8_000,
    enabled: !!id,
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: tasksApi.create,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useFixTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tasksApi.fix(id),
    onSuccess: (_data, id) => void qc.invalidateQueries({ queryKey: ["task", id] }),
  });
}
