"use client";

import { api } from "@/lib/api";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { toast } from "sonner";

export function useReminderPolling() {
  const queryClient = useQueryClient();
  // Track reminders currently being acked to avoid duplicate toasts
  const pendingAckIds = useRef(new Set<string>());

  const { data: dueReminders } = useQuery({
    queryKey: ["reminders", "due"],
    queryFn: () => api.getDueReminders(),
    refetchInterval: 60_000,
    // Silently ignore errors (user may not be logged in yet)
    retry: false,
  });

  useEffect(() => {
    if (!dueReminders?.length) return;

    for (const r of dueReminders) {
      if (pendingAckIds.current.has(r.id)) continue;
      pendingAckIds.current.add(r.id);

      toast(r.title, {
        description: r.description ?? undefined,
        duration: Number.POSITIVE_INFINITY,
        onDismiss: async () => {
          try {
            await api.ackReminder(r.id);
            queryClient.invalidateQueries({ queryKey: ["reminders"] });
          } finally {
            pendingAckIds.current.delete(r.id);
          }
        },
        onAutoClose: async () => {
          try {
            await api.ackReminder(r.id);
            queryClient.invalidateQueries({ queryKey: ["reminders"] });
          } finally {
            pendingAckIds.current.delete(r.id);
          }
        },
      });
    }
  }, [dueReminders, queryClient]);
}
