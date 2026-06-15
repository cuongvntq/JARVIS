"use client";

import type { Section } from "@/components/layout/Sidebar";
import { useCalendarEvents, useSyncCalendar } from "@/hooks/useCalendarEvents";
import { openInBrowser, useGoogleStatus } from "@/hooks/useGoogleCalendar";
import type { CalendarEventOut } from "@/lib/types/api";
import { useAuthStore } from "@/stores/authStore";
import { format } from "date-fns";
import { formatInTimeZone } from "date-fns-tz";
import { vi } from "date-fns/locale";
import { CalendarDays, ExternalLink, Loader2, MapPin, RefreshCw } from "lucide-react";
import { useState } from "react";

interface CalendarPageProps {
  onNavigate?: (section: Section) => void;
}

function eventDateKey(event: CalendarEventOut, timezone: string): string | null {
  if (event.is_all_day) return event.start_date ?? null;
  if (!event.start_at) return null;
  return formatInTimeZone(new Date(event.start_at), timezone, "yyyy-MM-dd");
}

function groupEventsByDay(
  events: CalendarEventOut[],
  timezone: string,
): Map<string, CalendarEventOut[]> {
  const groups = new Map<string, CalendarEventOut[]>();
  for (const event of events) {
    const key = eventDateKey(event, timezone);
    if (!key) continue;
    const list = groups.get(key) ?? [];
    list.push(event);
    groups.set(key, list);
  }
  return groups;
}

function dayLabel(dateKey: string, timezone: string): string {
  const now = new Date();
  const todayKey = formatInTimeZone(now, timezone, "yyyy-MM-dd");
  const tomorrowKey = formatInTimeZone(
    new Date(now.getTime() + 86_400_000),
    timezone,
    "yyyy-MM-dd",
  );
  if (dateKey === todayKey) return "Hôm nay";
  if (dateKey === tomorrowKey) return "Ngày mai";
  const [y, m, d] = dateKey.split("-").map(Number);
  return format(new Date(y, m - 1, d), "EEEE, dd/MM/yyyy", { locale: vi });
}

function EventRow({ event, timezone }: { event: CalendarEventOut; timezone: string }) {
  const timeLabel =
    event.is_all_day || !event.start_at
      ? "Cả ngày"
      : event.end_at
        ? `${formatInTimeZone(new Date(event.start_at), timezone, "HH:mm")} - ${formatInTimeZone(new Date(event.end_at), timezone, "HH:mm")}`
        : formatInTimeZone(new Date(event.start_at), timezone, "HH:mm");

  return (
    <div
      className="flex items-start gap-2.5 rounded-lg px-3 py-2.5"
      style={{ backgroundColor: "rgba(0,180,216,0.07)", border: "1px solid rgba(0,180,216,0.10)" }}
    >
      <CalendarDays size={11} className="mt-0.5 flex-shrink-0" style={{ color: "#00b4d8" }} />
      <div className="flex-1 min-w-0">
        <p className="text-xs leading-snug" style={{ color: "#dff3fd" }}>
          {event.summary}
        </p>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-[9px]" style={{ color: "#5e8a9e" }}>
            {timeLabel}
          </span>
          {event.location && (
            <span className="text-[9px] flex items-center gap-0.5" style={{ color: "#3a6a7e" }}>
              <MapPin size={9} />
              {event.location}
            </span>
          )}
        </div>
      </div>
      {event.html_link && (
        <button
          type="button"
          onClick={() => openInBrowser(event.html_link as string)}
          title="Mở trong Google Calendar"
          className="p-1 rounded transition-colors hover:bg-white/5 flex-shrink-0"
          style={{ color: "#5e8a9e" }}
        >
          <ExternalLink size={11} />
        </button>
      )}
    </div>
  );
}

export default function CalendarPage({ onNavigate }: CalendarPageProps) {
  const user = useAuthStore((s) => s.user);
  const timezone = user?.timezone ?? "UTC";

  const { data: status } = useGoogleStatus();
  const connected = status?.connected ?? false;

  const { data: events, isLoading, isError, isFetching } = useCalendarEvents();
  const syncCalendar = useSyncCalendar();
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);

  const grouped = events
    ? groupEventsByDay(events, timezone)
    : new Map<string, CalendarEventOut[]>();
  const sortedKeys = Array.from(grouped.keys()).sort();

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "#0b1929" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.12)" }}
      >
        <div className="flex items-center gap-3">
          <CalendarDays size={16} style={{ color: "#00b4d8" }} />
          <h1
            className="text-sm font-bold tracking-[0.25em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            LỊCH
          </h1>
          {lastSyncedAt && (
            <span className="text-[9px]" style={{ color: "#3a6a7e" }}>
              Đồng bộ lúc {formatInTimeZone(new Date(lastSyncedAt), timezone, "HH:mm dd/MM")}
            </span>
          )}
        </div>

        {connected && (
          <button
            type="button"
            onClick={() =>
              syncCalendar.mutate(undefined, {
                onSuccess: (result) => {
                  if (result.synced_at) setLastSyncedAt(result.synced_at);
                },
              })
            }
            disabled={syncCalendar.isPending || isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold tracking-[0.12em] transition-all hover:scale-105 disabled:opacity-50"
            style={{
              background: "linear-gradient(135deg, rgba(0,180,216,0.7), rgba(0,95,138,0.7))",
              color: "#dff3fd",
            }}
          >
            <RefreshCw size={11} className={syncCalendar.isPending ? "animate-spin" : ""} />
            ĐỒNG BỘ NGAY
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {!connected && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <CalendarDays size={28} style={{ color: "rgba(0,180,216,0.2)" }} />
            <p
              className="text-sm tracking-[0.1em] text-center"
              style={{ color: "rgba(0,180,216,0.3)" }}
            >
              Chưa kết nối Google Calendar
            </p>
            <button
              type="button"
              onClick={() => onNavigate?.("settings")}
              className="text-[10px] tracking-[0.1em] transition-colors hover:text-jarvis-accent"
              style={{ color: "#5e8a9e" }}
            >
              → Kết nối trong Cài đặt
            </button>
          </div>
        )}

        {connected && isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={18} className="animate-spin" style={{ color: "#5e8a9e" }} />
          </div>
        )}

        {connected && isError && (
          <p className="text-center py-16 text-sm" style={{ color: "#ff4444" }}>
            Không tải được lịch. Thử lại sau.
          </p>
        )}

        {connected && !isLoading && !isError && sortedKeys.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <CalendarDays size={28} style={{ color: "rgba(0,180,216,0.2)" }} />
            <p className="text-sm tracking-[0.1em]" style={{ color: "rgba(0,180,216,0.3)" }}>
              Không có sự kiện nào trong 14 ngày tới
            </p>
          </div>
        )}

        {connected && !isLoading && !isError && sortedKeys.length > 0 && (
          <div className="space-y-5">
            {sortedKeys.map((key) => (
              <div key={key}>
                <p
                  className="text-[9px] font-semibold tracking-[0.2em] mb-2"
                  style={{ color: "#3a6a7e" }}
                >
                  {dayLabel(key, timezone).toUpperCase()}
                </p>
                <div className="space-y-1.5">
                  {grouped.get(key)?.map((event) => (
                    <EventRow key={event.id} event={event} timezone={timezone} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
