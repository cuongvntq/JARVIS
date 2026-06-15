"use client";

import type { CalendarEventOut } from "@/lib/types/api";
import { formatInTimeZone } from "date-fns-tz";
import { CalendarDays } from "lucide-react";

interface TodayEventsProps {
  events: CalendarEventOut[];
  timezone: string;
  onNavigate?: (section: string) => void;
}

export default function TodayEvents({ events, timezone, onNavigate }: TodayEventsProps) {
  return (
    <div>
      <p className="text-[9px] font-semibold tracking-[0.2em] mb-3" style={{ color: "#3a6a7e" }}>
        SỰ KIỆN HÔM NAY
      </p>

      {events.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-4 rounded-lg gap-2"
          style={{ backgroundColor: "rgba(0,180,216,0.04)" }}
        >
          <CalendarDays size={16} style={{ color: "rgba(0,180,216,0.2)" }} />
          <p className="text-[10px]" style={{ color: "#3a6a7e" }}>
            Không có sự kiện nào hôm nay
          </p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {events.map((e) => (
            <button
              key={e.id}
              type="button"
              onClick={() => onNavigate?.("calendar")}
              className="w-full flex items-start gap-2.5 rounded-lg px-3 py-2.5 text-left transition-all hover:brightness-110 focus:outline-none"
              style={{
                backgroundColor: "rgba(0,180,216,0.07)",
                border: "1px solid rgba(0,180,216,0.10)",
              }}
            >
              <CalendarDays
                size={11}
                className="mt-0.5 flex-shrink-0"
                style={{ color: "#00b4d8" }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs leading-snug truncate" style={{ color: "#dff3fd" }}>
                  {e.summary}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[9px]" style={{ color: "#5e8a9e" }}>
                    {e.is_all_day || !e.start_at
                      ? "Cả ngày"
                      : formatInTimeZone(new Date(e.start_at), timezone, "HH:mm")}
                  </span>
                  {e.location && (
                    <span className="text-[9px] truncate" style={{ color: "#3a6a7e" }}>
                      {e.location}
                    </span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
