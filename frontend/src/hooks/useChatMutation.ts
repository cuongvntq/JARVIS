import { api } from "@/lib/api";
import type { ChatSendRequest } from "@/lib/types/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: ChatSendRequest) => api.sendMessage(req),
    onSuccess: (data, req) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      // Invalidate detail cache so history is fresh after sending in an existing conversation
      const convId = req.conversation_id ?? data.conversation_id;
      if (convId) {
        queryClient.invalidateQueries({ queryKey: ["conversation", convId] });
      }
      // AI may have called create_todo / create_note tools — keep lists in sync
      queryClient.invalidateQueries({ queryKey: ["todos"] });
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}
