import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { TodoCreate, TodoFilter } from "@/lib/types/api";

export function useTodos(filter: TodoFilter = "all") {
  return useQuery({
    queryKey: ["todos", filter],
    queryFn: () => api.listTodos({ filter }),
    staleTime: 30_000,
  });
}

export function useCreateTodo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TodoCreate) => api.createTodo(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
}

export function useCompleteTodo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.completeTodo(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
}

export function useDeleteTodo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteTodo(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] });
    },
  });
}
