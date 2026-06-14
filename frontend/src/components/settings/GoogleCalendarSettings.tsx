"use client";

import { useConnectGoogle, useDisconnectGoogle, useGoogleStatus } from "@/hooks/useGoogleCalendar";
import { AlertCircle, Calendar, CheckCircle, Loader2 } from "lucide-react";

export default function GoogleCalendarSettings() {
  const { data: status, isLoading } = useGoogleStatus();
  const connect = useConnectGoogle();
  const disconnect = useDisconnectGoogle();

  const connected = status?.connected ?? false;
  const busy = connect.isPending || disconnect.isPending;

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
        </>
      )}
    </section>
  );
}
