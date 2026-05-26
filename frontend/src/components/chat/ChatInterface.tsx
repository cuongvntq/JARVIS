"use client";

import { useState, useRef, useEffect } from "react";
import { Bot } from "lucide-react";
import MessageBubble, { type Message } from "./MessageBubble";
import ChatInput from "./ChatInput";
import { useSendMessage } from "@/hooks/useChatMutation";
import { ApiException } from "@/lib/types/api";

const WELCOME: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Xin chào! Tôi là J.A.R.V.I.S — trợ lý cá nhân của bạn.\n\nTôi có thể giúp bạn:\n• Quản lý todo và nhắc nhở\n• Ghi chú và lưu trữ thông tin\n• Trả lời câu hỏi bằng tiếng Việt\n\nBạn cần tôi giúp gì hôm nay?",
  timestamp: new Date(),
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { mutate: sendMessage, isPending } = useSendMessage();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isPending]);

  function handleSend() {
    if (!input.trim() || isPending) return;

    const content = input.trim();
    setInput("");

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    sendMessage(
      { content, conversation_id: conversationId, stream: false },
      {
        onSuccess: (data) => {
          // Replace temp message with server message, then add assistant reply
          setConversationId(data.conversation_id);
          setMessages((prev) => {
            const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
            return [
              ...withoutTemp,
              {
                id: data.user_message.id,
                role: "user",
                content: data.user_message.content,
                timestamp: new Date(data.user_message.created_at),
              } satisfies Message,
              {
                id: data.assistant_message.id,
                role: "assistant",
                content: data.assistant_message.content,
                timestamp: new Date(data.assistant_message.created_at),
              } satisfies Message,
            ];
          });
        },
        onError: (err) => {
          let errorText = "Xin lỗi, tôi gặp sự cố. Vui lòng thử lại.";
          if (err instanceof ApiException) {
            if (err.error.code === "llm_error") {
              errorText = "Dịch vụ AI tạm thời không khả dụng. Vui lòng thử lại sau ít phút.";
            } else if (err.statusCode === 429) {
              errorText = "Bạn đang gửi quá nhiều tin nhắn. Vui lòng đợi một chút.";
            }
          }
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: errorText,
              timestamp: new Date(),
            } satisfies Message,
          ]);
        },
      },
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <div
        className="px-6 py-4 border-b flex items-center gap-3 flex-shrink-0"
        style={{ borderColor: "rgba(0, 180, 216, 0.1)" }}
      >
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
          style={{
            background:
              "radial-gradient(circle, rgba(0, 180, 216, 0.55) 0%, rgba(0, 95, 138, 0.3) 100%)",
            border: "1px solid rgba(0, 180, 216, 0.35)",
            boxShadow: "0 0 12px rgba(0, 180, 216, 0.3)",
          }}
        >
          <Bot size={16} className="text-white" />
        </div>
        <div>
          <h2
            className="text-sm font-bold tracking-[0.15em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#dff3fd" }}
          >
            J.A.R.V.I.S
          </h2>
          <p className="text-[10px] tracking-[0.15em] flex items-center gap-1.5" style={{ color: "#00e676" }}>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-jarvis-success status-online" />
            READY
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isPending && (
          <div className="flex items-start gap-2.5 mb-5 msg-appear">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
              style={{
                background: "radial-gradient(circle, rgba(0, 180, 216, 0.55) 0%, rgba(0, 95, 138, 0.3) 100%)",
                border: "1px solid rgba(0, 180, 216, 0.35)",
                boxShadow: "0 0 8px rgba(0, 180, 216, 0.25)",
              }}
            >
              <Bot size={13} className="text-white" />
            </div>
            <div
              className="px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1.5"
              style={{ background: "rgba(15, 34, 53, 0.85)", border: "1px solid rgba(0, 180, 216, 0.15)" }}
            >
              <span className="dot-1 w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#00b4d8" }} />
              <span className="dot-2 w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#00b4d8" }} />
              <span className="dot-3 w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#00b4d8" }} />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInput value={input} onChange={setInput} onSend={handleSend} loading={isPending} />
    </div>
  );
}
