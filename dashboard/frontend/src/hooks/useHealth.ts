import { useQuery } from "@tanstack/react-query";
import { health as healthApi } from "@/lib/api";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => healthApi.get(),
    refetchInterval: 15_000,
  });
}

export function useModelReachability() {
  return useQuery({
    queryKey: ["health", "models"],
    queryFn: () => healthApi.models(),
    refetchInterval: 30_000,
  });
}

export function useHealthErrors() {
  return useQuery({
    queryKey: ["health", "errors"],
    queryFn: () => healthApi.errors(),
    refetchInterval: 30_000,
  });
}
