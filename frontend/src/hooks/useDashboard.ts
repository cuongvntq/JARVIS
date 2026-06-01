import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.getDashboardToday(),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000, // refetch every 5 minutes
  });
}
