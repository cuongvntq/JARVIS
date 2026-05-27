import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useConversations(limit = 20) {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.listConversations(limit),
    staleTime: 30_000,
  });
}

export function useConversationDetail(id: string | null) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: () => api.getConversation(id!),
    enabled: !!id,
    staleTime: 60_000,
  });
}
