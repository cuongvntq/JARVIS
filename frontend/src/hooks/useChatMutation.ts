import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ChatSendRequest } from "@/lib/types/api";

export function useSendMessage() {
  return useMutation({
    mutationFn: (req: ChatSendRequest) => api.sendMessage(req),
  });
}
