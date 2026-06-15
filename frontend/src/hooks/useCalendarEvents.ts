import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const SELECTED_KEY = ["google-calendar", "selected"];
const EVENTS_KEY = ["google-calendar", "events"];
const DASHBOARD_KEY = ["dashboard"];

export function useCalendarEvents(timeMin?: string, timeMax?: string) {
  return useQuery({
    queryKey: [...EVENTS_KEY, timeMin ?? null, timeMax ?? null],
    queryFn: () => api.googleListEvents(timeMin, timeMax),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useSyncCalendar() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.googleSyncNow(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EVENTS_KEY });
      queryClient.invalidateQueries({ queryKey: DASHBOARD_KEY });
    },
  });
}

export function useCalendarSelection() {
  return useQuery({
    queryKey: SELECTED_KEY,
    queryFn: () => api.googleGetSelected(),
    staleTime: 30_000,
  });
}

export function useSetCalendarSelection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (calendarIds: string[]) => api.googleSetSelected(calendarIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SELECTED_KEY });
      queryClient.invalidateQueries({ queryKey: EVENTS_KEY });
      queryClient.invalidateQueries({ queryKey: DASHBOARD_KEY });
    },
  });
}
