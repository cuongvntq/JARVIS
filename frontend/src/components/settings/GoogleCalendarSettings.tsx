"use client";

import {
  useCalendarSelection,
  useSetCalendarSelection,
  useSyncCalendar,
} from "@/hooks/useCalendarEvents";
import { useConnectGoogle, useDisconnectGoogle, useGoogleStatus } from "@/hooks/useGoogleCalendar";
import { AlertCircle, Calendar, CheckCircle, Loader2, RefreshCw } from "lucide-react";

export default function GoogleCalendarSettings() {
  const { data: status, isLoading } = useGoogleStatus();
  const connect = useConnectGoogle();
  const disconnect = useDisconnectGoogle();

  const connected = status?.connected ?? false;
  const busy = connect.isPending || disconnect.isPending;

  const { data: calendars, isLoading: calendarsLoading } = useCalendarSelection();
  const setSelection = useSetCalendarSelection();
  const syncCalendar = useSyncCalendar();

  function toggleCalendar(googleCalendarId: string, checked: boolean) {
    if (!calendars) return;
    const selectedIds = calendars
      .filter((c) =>
        c.google_calendar_id === googleCalendarId ? checked : c.selected,
      )
      .map((c) => c.google_calendar_id);
    setSelection.mutate(selectedIds);
  }

  const buttonStyle = {
    fontFamily: "var(--font-orbitron)",
    background: connected
      ? "rgba(255, 68, 68, 0.12)"
      : "linear-gradient(135deg, rgba(0, 180, 216, 0.8), rgba(0, 95, 138, 0.8))",
    color: connected ? "#ff6b6b" : "#dff3fd",
    border: connected ? "1px solid rgba(255, 68, 68, 0.3)" : "1px solid rgba(0, 180, 216, 0.3)",
  };

  return (
    <section className="space-y-4 max-w-lg">
      <div className="flex items-center gap-2 mb-3">
        <Calendar size={13} style={{ color: "#00b4d8" }} />
        <span
          className="text-[10px] font-semibold tracking-[0.2em] uppercase"
          style={{ fontFamily: "var(--font-orbitron)", color: "#5e8a9e" }}
        >
          Google Calendar
        </span>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-xs" style={{ color: "#5e8a9e" }}>
          <Loader2 size={13} className="animate-spin" />
          Đang tải trạng thái...
        </div>
      ) : (
        <>
          {connected ? (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ backgroundColor: "rgba(0, 230, 118, 0.08)", color: "#00e676" }}
            >
              <CheckCircle size={13} />
              <span>
                Đã kết nối: <strong>{status?.email}</strong>
              </span>
            </div>
          ) : (
            <p className="text-xs" style={{ color: "#5e8a9e" }}>
              Kết nối Google Calendar để JARVIS đọc lịch của bạn (chỉ quyền đọc).
            </p>
          )}

          {connect.isPending && (
            <div className="flex items-center gap-2 text-xs" style={{ color: "#00b4d8" }}>
              <Loader2 size={13} className="animate-spin" />
              Đang chờ xác thực trên trình duyệt...
            </div>
          )}

          {(connect.isError || disconnect.isError) && (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ backgroundColor: "rgba(255, 68, 68, 0.08)", color: "#ff4444" }}
            >
              <AlertCircle size={13} />
              {(connect.error as Error)?.message ??
                (disconnect.error as Error)?.message ??
                "Thao tác thất bại, thử lại sau"}
            </div>
          )}

          <button
            type="button"
            disabled={busy}
            onClick={() => (connected ? disconnect.mutate() : connect.mutate())}
            className="px-6 py-2.5 rounded-lg text-xs font-semibold tracking-[0.15em] uppercase transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={buttonStyle}
          >
            {busy ? "Đang xử lý..." : connected ? "Ngắt kết nối" : "Kết nối Google Calendar"}
          </button>

          {connected && (
            <div className="space-y-2 pt-2">
              <p
                className="text-[9px] font-semibold tracking-[0.2em]"
                style={{ color: "#3a6a7e" }}
              >
                CHỌN LỊCH ĐỒNG BỘ
              </p>

              {calendarsLoading ? (
                <div className="flex items-center gap-2 text-xs" style={{ color: "#5e8a9e" }}>
                  <Loader2 size={13} className="animate-spin" />
                  Đang tải danh sách lịch...
                </div>
              ) : calendars && calendars.length > 0 ? (
                <div className="space-y-1.5">
                  {calendars.map((c) => (
                    <label
                      key={c.google_calendar_id}
                      className="flex items-center gap-2 text-xs cursor-pointer"
                      style={{ color: "#dff3fd" }}
                    >
                      <input
                        type="checkbox"
                        checked={c.selected}
                        disabled={setSelection.isPending}
                        onChange={(e) => toggleCalendar(c.google_calendar_id, e.target.checked)}
                        className="accent-[#00b4d8]"
                      />
                      <span>
                        {c.calendar_summary}
                        {c.is_primary && (
                          <span style={{ color: "#3a6a7e" }}> (chính)</span>
                        )}
                      </span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-xs" style={{ color: "#5e8a9e" }}>
                  Chưa có lịch nào. Nhấn "Đồng bộ ngay" để tải danh sách.
                </p>
              )}

              {(setSelection.isError || syncCalendar.isError) && (
                <div
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
                  style={{ backgroundColor: "rgba(255, 68, 68, 0.08)", color: "#ff4444" }}
                >
                  <AlertCircle size={13} />
                  {(setSelection.error as Error)?.message ??
                    (syncCalendar.error as Error)?.message ??
                    "Thao tác thất bại, thử lại sau"}
                </div>
              )}

              <button
                type="button"
                disabled={syncCalendar.isPending}
                onClick={() => syncCalendar.mutate()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[10px] font-semibold tracking-[0.15em] uppercase transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: "linear-gradient(135deg, rgba(0, 180, 216, 0.8), rgba(0, 95, 138, 0.8))",
                  color: "#dff3fd",
                }}
              >
                <RefreshCw size={11} className={syncCalendar.isPending ? "animate-spin" : ""} />
                {syncCalendar.isPending ? "Đang đồng bộ..." : "Đồng bộ ngay"}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
