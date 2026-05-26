"use client";

import { Send } from "lucide-react";
import type { KeyboardEvent } from "react";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  loading: boolean;
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  loading,
}: ChatInputProps) {
  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !loading) {
      e.preventDefault();
      onSend();
    }
  }

  const canSend = !loading && value.trim().length > 0;

  return (
    <div
      className="px-5 pb-5 pt-3 border-t"
      style={{ borderColor: "rgba(0, 180, 216, 0.1)" }}
    >
      <div
        className="flex items-end gap-3 rounded-xl px-4 py-3"
        style={{
          background: "rgba(11, 25, 41, 0.9)",
          border: "1px solid rgba(0, 180, 216, 0.18)",
        }}
      >
        <textarea
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            e.currentTarget.style.height = "auto";
            e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 120)}px`;
          }}
          onKeyDown={handleKey}
          disabled={loading}
          rows={1}
          placeholder="Nhắn tin với JARVIS... (Enter để gửi, Shift+Enter xuống dòng)"
          className="flex-1 bg-transparent resize-none text-sm leading-relaxed"
          style={{
            color: "#dff3fd",
            caretColor: "#00b4d8",
            maxHeight: "120px",
            fontFamily: "var(--font-inter)",
          }}
        />

        <button
          type="button"
          onClick={onSend}
          disabled={!canSend}
          className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-200"
          style={{
            background: canSend
              ? "rgba(0, 180, 216, 0.75)"
              : "rgba(0, 180, 216, 0.08)",
            border: "1px solid rgba(0, 180, 216, 0.25)",
            cursor: canSend ? "pointer" : "not-allowed",
            boxShadow: canSend ? "0 0 10px rgba(0, 180, 216, 0.3)" : "none",
          }}
        >
          {loading ? (
            <div className="flex gap-0.5 items-center">
              <span
                className="dot-1 w-1 h-1 rounded-full"
                style={{ backgroundColor: "#00b4d8" }}
              />
              <span
                className="dot-2 w-1 h-1 rounded-full"
                style={{ backgroundColor: "#00b4d8" }}
              />
              <span
                className="dot-3 w-1 h-1 rounded-full"
                style={{ backgroundColor: "#00b4d8" }}
              />
            </div>
          ) : (
            <Send
              size={15}
              style={{ color: canSend ? "white" : "#5e8a9e" }}
            />
          )}
        </button>
      </div>

      <p
        className="text-center text-[10px] mt-2 tracking-wider"
        style={{ color: "rgba(94, 138, 158, 0.4)" }}
      >
        J.A.R.V.I.S có thể mắc lỗi. Kiểm tra thông tin quan trọng.
      </p>
    </div>
  );
}
