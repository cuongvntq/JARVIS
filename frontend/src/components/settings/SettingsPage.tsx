"use client";

import { useState, useEffect } from "react";
import { Settings, User, Globe, Bot, CheckCircle, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useUpdateProfile } from "@/hooks/useSettings";

const TIMEZONES = [
  { value: "Asia/Ho_Chi_Minh", label: "Hà Nội / TP. HCM (UTC+7)" },
  { value: "Asia/Bangkok", label: "Bangkok (UTC+7)" },
  { value: "Asia/Singapore", label: "Singapore (UTC+8)" },
  { value: "Asia/Tokyo", label: "Tokyo (UTC+9)" },
  { value: "Asia/Shanghai", label: "Thượng Hải (UTC+8)" },
  { value: "Asia/Seoul", label: "Seoul (UTC+9)" },
  { value: "Europe/London", label: "London (UTC+0/+1)" },
  { value: "Europe/Paris", label: "Paris (UTC+1/+2)" },
  { value: "America/New_York", label: "New York (UTC-5/-4)" },
  { value: "America/Los_Angeles", label: "Los Angeles (UTC-8/-7)" },
  { value: "UTC", label: "UTC (UTC+0)" },
];

const LOCALES = [
  { value: "vi-VN", label: "Tiếng Việt" },
  { value: "en-US", label: "English (US)" },
];

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const { mutate: updateProfile, reset: resetMutation, isPending, isSuccess, isError, error } = useUpdateProfile();

  const [name, setName] = useState("");
  const [assistantName, setAssistantName] = useState("");
  const [timezone, setTimezone] = useState("");
  const [locale, setLocale] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setAssistantName(user.assistant_name);
      setTimezone(user.timezone);
      setLocale(user.locale);
    }
  }, [user]);

  function handleFieldChange(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setter(e.target.value);
      resetMutation();
      setValidationError(null);
    };
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setValidationError("Tên hiển thị không được để trống");
      return;
    }
    if (!assistantName.trim()) {
      setValidationError("Tên trợ lý không được để trống");
      return;
    }
    updateProfile({
      name: name.trim(),
      assistant_name: assistantName.trim(),
      timezone,
      locale,
    });
  }

  const inputClass =
    "w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-150 focus:ring-1";
  const inputStyle = {
    backgroundColor: "#0b1929",
    border: "1px solid rgba(0, 180, 216, 0.2)",
    color: "#dff3fd",
  };
  const inputFocusStyle = { "--tw-ring-color": "rgba(0, 180, 216, 0.5)" } as React.CSSProperties;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="px-6 py-5 border-b flex items-center gap-3 flex-shrink-0"
        style={{ borderColor: "rgba(0, 180, 216, 0.12)" }}
      >
        <Settings size={18} style={{ color: "#00b4d8" }} />
        <h2
          className="text-sm font-bold tracking-[0.2em] uppercase"
          style={{ fontFamily: "var(--font-orbitron)", color: "#dff3fd" }}
        >
          Settings
        </h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <form onSubmit={handleSubmit} className="max-w-lg space-y-8">

          {/* Profile section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 mb-3">
              <User size={13} style={{ color: "#00b4d8" }} />
              <span
                className="text-[10px] font-semibold tracking-[0.2em] uppercase"
                style={{ fontFamily: "var(--font-orbitron)", color: "#5e8a9e" }}
              >
                Hồ sơ
              </span>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="settings-name"
                className="block text-xs tracking-wide"
                style={{ color: "#5e8a9e" }}
              >
                Tên hiển thị
              </label>
              <input
                id="settings-name"
                type="text"
                value={name}
                onChange={handleFieldChange(setName)}
                minLength={1}
                maxLength={100}
                className={inputClass}
                style={{ ...inputStyle, ...inputFocusStyle }}
                placeholder="Nhập tên của bạn"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="settings-email"
                className="block text-xs tracking-wide"
                style={{ color: "#5e8a9e" }}
              >
                Email
              </label>
              <input
                id="settings-email"
                type="email"
                value={user?.email ?? ""}
                disabled
                className={`${inputClass} opacity-40 cursor-not-allowed`}
                style={inputStyle}
              />
              <p className="text-[10px]" style={{ color: "rgba(94, 138, 158, 0.6)" }}>
                Không thể thay đổi email
              </p>
            </div>
          </section>

          {/* Assistant section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 mb-3">
              <Bot size={13} style={{ color: "#00b4d8" }} />
              <span
                className="text-[10px] font-semibold tracking-[0.2em] uppercase"
                style={{ fontFamily: "var(--font-orbitron)", color: "#5e8a9e" }}
              >
                Trợ lý AI
              </span>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="settings-assistant-name"
                className="block text-xs tracking-wide"
                style={{ color: "#5e8a9e" }}
              >
                Tên trợ lý
              </label>
              <input
                id="settings-assistant-name"
                type="text"
                value={assistantName}
                onChange={handleFieldChange(setAssistantName)}
                minLength={1}
                maxLength={50}
                className={inputClass}
                style={{ ...inputStyle, ...inputFocusStyle }}
                placeholder="J.A.R.V.I.S"
              />
              <p className="text-[10px]" style={{ color: "rgba(94, 138, 158, 0.6)" }}>
                Tên bạn muốn gọi trợ lý AI của mình
              </p>
            </div>
          </section>

          {/* Preferences section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 mb-3">
              <Globe size={13} style={{ color: "#00b4d8" }} />
              <span
                className="text-[10px] font-semibold tracking-[0.2em] uppercase"
                style={{ fontFamily: "var(--font-orbitron)", color: "#5e8a9e" }}
              >
                Ngôn ngữ & Múi giờ
              </span>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="settings-timezone"
                className="block text-xs tracking-wide"
                style={{ color: "#5e8a9e" }}
              >
                Múi giờ
              </label>
              <select
                id="settings-timezone"
                value={timezone}
                onChange={handleFieldChange(setTimezone)}
                className={inputClass}
                style={{ ...inputStyle, ...inputFocusStyle }}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value} style={{ backgroundColor: "#0b1929" }}>
                    {tz.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="settings-locale"
                className="block text-xs tracking-wide"
                style={{ color: "#5e8a9e" }}
              >
                Ngôn ngữ
              </label>
              <select
                id="settings-locale"
                value={locale}
                onChange={handleFieldChange(setLocale)}
                className={inputClass}
                style={{ ...inputStyle, ...inputFocusStyle }}
              >
                {LOCALES.map((l) => (
                  <option key={l.value} value={l.value} style={{ backgroundColor: "#0b1929" }}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* Status messages */}
          {validationError && (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ backgroundColor: "rgba(255, 68, 68, 0.08)", color: "#ff4444" }}
            >
              <AlertCircle size={13} />
              {validationError}
            </div>
          )}
          {isSuccess && (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ backgroundColor: "rgba(0, 230, 118, 0.08)", color: "#00e676" }}
            >
              <CheckCircle size={13} />
              Đã lưu thay đổi
            </div>
          )}
          {isError && (
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs"
              style={{ backgroundColor: "rgba(255, 68, 68, 0.08)", color: "#ff4444" }}
            >
              <AlertCircle size={13} />
              {(error as Error)?.message ?? "Không thể lưu, thử lại sau"}
            </div>
          )}

          {/* Save button */}
          <button
            type="submit"
            disabled={isPending}
            className="px-6 py-2.5 rounded-lg text-xs font-semibold tracking-[0.15em] uppercase transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              fontFamily: "var(--font-orbitron)",
              background: isPending
                ? "rgba(0, 180, 216, 0.2)"
                : "linear-gradient(135deg, rgba(0, 180, 216, 0.8), rgba(0, 95, 138, 0.8))",
              color: "#dff3fd",
              border: "1px solid rgba(0, 180, 216, 0.3)",
            }}
          >
            {isPending ? "Đang lưu..." : "Lưu thay đổi"}
          </button>
        </form>
      </div>
    </div>
  );
}
