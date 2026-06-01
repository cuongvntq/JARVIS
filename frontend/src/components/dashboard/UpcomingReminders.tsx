"use client";

import { Bell } from "lucide-react";
import { formatInTimeZone } from "date-fns-tz";
import type { ReminderOut } from "@/lib/types/api";

interface UpcomingRemindersProps {
  reminders: ReminderOut[];
  timezone: string;
  onNavigate?: (section: string) => void;
}

function formatCountdown(remindAt: string): string {
  const diff = new Date(remindAt).getTime() - Date.now();
  if (diff <= 0) return "Vừa đến hạn";
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `còn ${mins} phút`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `còn ${hours} giờ`;
  return `còn ${Math.floor(hours / 24)} ngày`;
}

export default function UpcomingReminders({
  reminders,
  timezone,
  onNavigate,
}: UpcomingRemindersProps) {
  return (
    <div>
      <p
        className="text-[9px] font-semibold tracking-[0.2em] mb-3"
        style={{ color: "#3a6a7e" }}
      >
        NHẮC NHỞ SẮP TỚI
      </p>

      {reminders.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-4 rounded-lg gap-2"
          style={{ backgroundColor: "rgba(0,180,216,0.04)" }}
        >
          <Bell size={16} style={{ color: "rgba(0,180,216,0.2)" }} />
          <p className="text-[10px]" style={{ color: "#3a6a7e" }}>
            Không có nhắc nhở nào sắp tới
          </p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {reminders.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => onNavigate?.("reminders")}
              className="w-full flex items-start gap-2.5 rounded-lg px-3 py-2.5 text-left transition-all hover:brightness-110 focus:outline-none"
              style={{
                backgroundColor: "rgba(0,180,216,0.07)",
                border: "1px solid rgba(0,180,216,0.10)",
              }}
            >
              <Bell size={11} className="mt-0.5 flex-shrink-0" style={{ color: "#00b4d8" }} />
              <div className="flex-1 min-w-0">
                <p className="text-xs leading-snug truncate" style={{ color: "#dff3fd" }}>
                  {r.title}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[9px]" style={{ color: "#5e8a9e" }}>
                    ⏰ {formatInTimeZone(new Date(r.remind_at), timezone, "HH:mm dd/MM")}
                  </span>
                  <span className="text-[9px]" style={{ color: "#3a6a7e" }}>
                    {formatCountdown(r.remind_at)}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
