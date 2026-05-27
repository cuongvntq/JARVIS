import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ChatSendRequest } from "@/lib/types/api";

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: ChatSendRequest) => api.sendMessage(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
