import { api } from "@/lib/api";
import type { MemoryCreate, MemoryType, MemoryUpdate } from "@/lib/types/api";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export function useMemories(type?: MemoryType) {
  return useInfiniteQuery({
    queryKey: ["memories", type ?? ""],
    queryFn: ({ pageParam }) => api.listMemories({ type, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 30_000,
  });
}

export function useCreateMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MemoryCreate) => api.createMemory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });
}

export function useUpdateMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MemoryUpdate }) => api.updateMemory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });
}

export function useDeleteMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });
}
