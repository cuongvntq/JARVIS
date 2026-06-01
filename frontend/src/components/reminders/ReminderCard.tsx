"use client";

import { BanIcon, Trash2 } from "lucide-react";
import { formatInTimeZone } from "date-fns-tz";
import { cn } from "@/lib/utils";
import type { ReminderOut, ReminderStatus } from "@/lib/types/api";

interface ReminderCardProps {
  reminder: ReminderOut;
  timezone: string;
  onCancel: (id: string) => void;
  onDelete: (id: string) => void;
  isCancelPending: boolean;
  isDeletePending: boolean;
}

const STATUS_CONFIG: Record<ReminderStatus, { label: string; color: string; bg: string; strip: string }> = {
  pending: { label: "ĐANG CHỜ", color: "#00b4d8", bg: "rgba(0,180,216,0.12)", strip: "bg-jarvis-accent/60" },
  sending: { label: "ĐANG GỬI", color: "#ff9800", bg: "rgba(255,152,0,0.12)", strip: "bg-yellow-500/70" },
  sent: { label: "ĐÃ GỬI", color: "#00e676", bg: "rgba(0,230,118,0.10)", strip: "bg-green-500/60" },
  failed: { label: "THẤT BẠI", color: "#ff4444", bg: "rgba(255,68,68,0.12)", strip: "bg-jarvis-danger/70" },
  cancelled: { label: "ĐÃ HỦY", color: "#5e8a9e", bg: "rgba(94,138,158,0.12)", strip: "bg-jarvis-muted/40" },
};

function formatCountdown(remindAt: string): string {
  const diff = new Date(remindAt).getTime() - Date.now();
  if (diff <= 0) return "Vừa đến hạn";
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `còn ${mins} phút`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `còn ${hours} giờ`;
  const days = Math.floor(hours / 24);
  return `còn ${days} ngày`;
}

export default function ReminderCard({
  reminder,
  timezone,
  onCancel,
  onDelete,
  isCancelPending,
  isDeletePending,
}: ReminderCardProps) {
  const cfg = STATUS_CONFIG[reminder.status];
  const isDone = reminder.status === "sent" || reminder.status === "cancelled" || reminder.status === "failed";
  const canCancel = reminder.status === "pending" || reminder.status === "sending";

  return (
    <div
      className={cn(
        "group flex items-start gap-0 rounded-lg overflow-hidden border transition-all duration-150",
        isDone ? "opacity-55" : "hover:border-jarvis-accent/30",
      )}
      style={{
        backgroundColor: "#0a1a2e",
        borderColor: isDone ? "rgba(94,138,158,0.15)" : "rgba(0,180,216,0.15)",
      }}
    >
      {/* Status strip */}
      <div className={cn("w-1 self-stretch flex-shrink-0", cfg.strip)} />

      {/* Content */}
      <div className="flex-1 min-w-0 px-3 py-3">
        <p
          className={cn("text-sm leading-snug break-words", isDone && "line-through")}
          style={{ color: isDone ? "#5e8a9e" : "#dff3fd" }}
        >
          {reminder.title}
        </p>

        {reminder.description && (
          <p className="text-xs mt-0.5 truncate" style={{ color: "#4a7a8e" }}>
            {reminder.description}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5">
          {/* Status badge */}
          <span
            className="text-[9px] font-semibold tracking-[0.1em] px-1.5 py-0.5 rounded"
            style={{ color: cfg.color, backgroundColor: cfg.bg }}
          >
            {cfg.label}
          </span>

          {/* Remind time */}
          <span className="text-[10px]" style={{ color: "#5e8a9e" }}>
            ⏰ {formatInTimeZone(new Date(reminder.remind_at), timezone, "HH:mm dd/MM/yyyy")}
          </span>

          {/* Countdown — only for active reminders */}
          {!isDone && (
            <span className="text-[10px]" style={{ color: "#3a6a7e" }}>
              {formatCountdown(reminder.remind_at)}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 flex-shrink-0 mt-2.5 mr-2.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
        {canCancel && (
          <button
            type="button"
            onClick={() => onCancel(reminder.id)}
            disabled={isCancelPending}
            title="Hủy nhắc nhở"
            className="p-1 rounded transition-colors hover:text-yellow-400 focus:outline-none disabled:opacity-40"
            style={{ color: "#3a6a7e" }}
          >
            <BanIcon size={12} />
          </button>
        )}
        <button
          type="button"
          onClick={() => onDelete(reminder.id)}
          disabled={isDeletePending}
          title="Xóa nhắc nhở"
          className="p-1 rounded transition-colors hover:text-jarvis-danger focus:outline-none focus:text-jarvis-danger disabled:opacity-40"
          style={{ color: "#3a6a7e" }}
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}
