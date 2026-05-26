import { Bot, User } from "lucide-react";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string;
  timestamp: Date;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end items-start gap-2.5 mb-5 msg-appear">
        <div className="max-w-[68%]">
          <div
            className="px-4 py-3 rounded-2xl rounded-tr-sm text-sm leading-relaxed"
            style={{
              background:
                "linear-gradient(135deg, rgba(0, 95, 138, 0.8), rgba(0, 180, 216, 0.4))",
              border: "1px solid rgba(0, 180, 216, 0.25)",
              color: "#dff3fd",
            }}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
          <p
            className="text-[10px] mt-1 text-right pr-1"
            style={{ color: "rgba(0, 180, 216, 0.35)" }}
          >
            {formatTime(message.timestamp)}
          </p>
        </div>
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{
            background: "rgba(0, 180, 216, 0.12)",
            border: "1px solid rgba(0, 180, 216, 0.25)",
          }}
        >
          <User size={13} style={{ color: "#00b4d8" }} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5 mb-5 msg-appear">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{
          background:
            "radial-gradient(circle, rgba(0, 180, 216, 0.55) 0%, rgba(0, 95, 138, 0.3) 100%)",
          border: "1px solid rgba(0, 180, 216, 0.35)",
          boxShadow: "0 0 8px rgba(0, 180, 216, 0.25)",
        }}
      >
        <Bot size={13} className="text-white" />
      </div>
      <div className="max-w-[75%]">
        <div
          className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm leading-relaxed"
          style={{
            background: "rgba(15, 34, 53, 0.85)",
            border: "1px solid rgba(0, 180, 216, 0.15)",
            color: "#dff3fd",
          }}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex items-center gap-2 mt-1 pl-1">
          <p
            className="text-[10px]"
            style={{ color: "rgba(0, 180, 216, 0.35)" }}
          >
            {formatTime(message.timestamp)}
          </p>
          {message.model && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded tracking-wider"
              style={{
                background: "rgba(0, 180, 216, 0.07)",
                color: "rgba(0, 180, 216, 0.45)",
                border: "1px solid rgba(0, 180, 216, 0.12)",
                fontFamily: "var(--font-orbitron)",
              }}
            >
              {message.model}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
