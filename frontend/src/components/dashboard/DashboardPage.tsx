"use client";

import type { Section } from "@/components/layout/Sidebar";
import { useDashboard } from "@/hooks/useDashboard";
import { useAuthStore } from "@/stores/authStore";
import { formatInTimeZone } from "date-fns-tz";
import { LayoutDashboard, Loader2, RefreshCw } from "lucide-react";
import MemoryCount from "./MemoryCount";
import TodayEvents from "./TodayEvents";
import TodayStats from "./TodayStats";
import UpcomingReminders from "./UpcomingReminders";

interface DashboardPageProps {
  onNavigate?: (section: Section) => void;
}

export default function DashboardPage({ onNavigate }: DashboardPageProps) {
  const user = useAuthStore((s) => s.user);
  const timezone = user?.timezone ?? "UTC";

  const { data, isLoading, isError, refetch, isFetching } = useDashboard();

  const asOf = data?.as_of
    ? formatInTimeZone(new Date(data.as_of), timezone, "HH:mm dd/MM/yyyy")
    : null;

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "#0b1929" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.12)" }}
      >
        <div className="flex items-center gap-3">
          <LayoutDashboard size={16} style={{ color: "#00b4d8" }} />
          <h1
            className="text-sm font-bold tracking-[0.25em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            DASHBOARD
          </h1>
          {asOf && (
            <span className="text-[9px]" style={{ color: "#3a6a7e" }}>
              {asOf}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          title="Làm mới"
          className="p-1.5 rounded transition-colors hover:bg-white/5 disabled:opacity-40"
          style={{ color: "#5e8a9e" }}
        >
          <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={18} className="animate-spin" style={{ color: "#5e8a9e" }} />
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <p className="text-sm" style={{ color: "#ff4444" }}>
              Không tải được dashboard. Thử lại sau.
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="text-[10px] tracking-[0.1em] transition-colors hover:text-jarvis-accent"
              style={{ color: "#5e8a9e" }}
            >
              Thử lại
            </button>
          </div>
        )}

        {!isLoading && !isError && data && (
          <div className="space-y-6 max-w-lg">
            {/* Today's Todo Stats */}
            <TodayStats count={data.todos_count} onNavigate={(s) => onNavigate?.(s as Section)} />

            {/* Divider */}
            <div style={{ height: 1, backgroundColor: "rgba(0,180,216,0.07)" }} />

            {/* Upcoming Reminders */}
            <UpcomingReminders
              reminders={data.reminders_upcoming}
              timezone={timezone}
              onNavigate={(s) => onNavigate?.(s as Section)}
            />

            {/* Divider */}
            <div style={{ height: 1, backgroundColor: "rgba(0,180,216,0.07)" }} />

            {/* Today's Events */}
            <TodayEvents
              events={data.events_today}
              timezone={timezone}
              onNavigate={(s) => onNavigate?.(s as Section)}
            />

            {/* Divider */}
            <div style={{ height: 1, backgroundColor: "rgba(0,180,216,0.07)" }} />

            {/* Memory Count */}
            <MemoryCount
              count={data.memories_count}
              onNavigate={(s) => onNavigate?.(s as Section)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
