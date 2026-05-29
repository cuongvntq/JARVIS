"use client";

import { useConversationDetail } from "@/hooks/useConversations";
import { api } from "@/lib/api";
import { ApiException } from "@/lib/types/api";
import { useQueryClient } from "@tanstack/react-query";
import { Bot, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ChatInput from "./ChatInput";
import MessageBubble, { type Message } from "./MessageBubble";

const WELCOME: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Xin chào! Tôi là J.A.R.V.I.S — trợ lý cá nhân của bạn.\n\nTôi có thể giúp bạn:\n• Quản lý todo và nhắc nhở\n• Ghi chú và lưu trữ thông tin\n• Trả lời câu hỏi bằng tiếng Việt\n\nBạn cần tôi giúp gì hôm nay?",
  timestamp: new Date(),
};

interface ChatInterfaceProps {
  conversationId: string | null;
  onConversationCreated: (id: string) => void;
}

export default function ChatInterface({
  conversationId,
  onConversationCreated,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Guards to prevent message wipe / spinner when conversation is freshly created mid-stream
  const justCreatedConvIdRef = useRef<string | null>(null);
  const skipNextHistoryLoadRef = useRef(false);

  const { data: convDetail, isLoading: isLoadingHistory } = useConversationDetail(conversationId);

  const prevConvId = useRef<string | null>(null);
  useEffect(() => {
    if (conversationId === prevConvId.current) return;
    prevConvId.current = conversationId;

    if (conversationId === null) {
      setMessages([WELCOME]);
      return;
    }
    // Skip reset when this is the conversation we just created during streaming
    if (conversationId === justCreatedConvIdRef.current) {
      justCreatedConvIdRef.current = null;
      return;
    }
    setMessages([]);
  }, [conversationId]);

  useEffect(() => {
    if (!convDetail || convDetail.id !== conversationId) return;
    // Skip history load for just-created conversations — streaming messages are already in state
    if (skipNextHistoryLoadRef.current) {
      skipNextHistoryLoadRef.current = false;
      return;
    }
    setMessages(
      convDetail.messages.map((m) => ({
        id: m.id,
        role: m.role as Message["role"],
        content: m.content,
        timestamp: new Date(m.created_at),
      })),
    );
  }, [convDetail, conversationId]);

  useEffect(() => {
    if (messages.length > 0 || isStreaming) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming]);

  async function handleSend() {
    if (!input.trim() || isStreaming) return;

    const content = input.trim();
    setInput("");
    setIsStreaming(true);

    const tempUserId = `temp-user-${crypto.randomUUID()}`;
    const tempAssistantId = `temp-assistant-${crypto.randomUUID()}`;

    // Track new conversation id from meta event; only passed to parent after stream ends
    let newConvId: string | null = null;
    // Only call onConversationCreated if stream completed successfully (done event received).
    // If stream errors after meta, backend rolls back → conv_id no longer exists in DB.
    let streamSucceeded = false;

    setMessages((prev) => [
      ...prev,
      { id: tempUserId, role: "user", content, timestamp: new Date() },
      {
        id: tempAssistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        streaming: true,
        toolStatus: null,
      },
    ]);

    try {
      for await (const event of api.sendMessageStream({
        content,
        conversation_id: conversationId,
        stream: true,
      })) {
        switch (event.type) {
          case "meta":
            // Save new conv id but do NOT call onConversationCreated yet —
            // doing so would change the prop and trigger setMessages([]) mid-stream
            if (!conversationId) {
              newConvId = event.conversation_id;
            }
            setMessages((prev) =>
              prev.map((m) => (m.id === tempUserId ? { ...m, id: event.user_message_id } : m)),
            );
            break;

          case "tool_start":
            setMessages((prev) =>
              prev.map((m) => (m.id === tempAssistantId ? { ...m, toolStatus: event.label } : m)),
            );
            break;

          case "tool_done":
            setMessages((prev) =>
              prev.map((m) => (m.id === tempAssistantId ? { ...m, toolStatus: null } : m)),
            );
            break;

          case "delta":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId ? { ...m, content: m.content + event.content } : m,
              ),
            );
            bottomRef.current?.scrollIntoView({ behavior: "smooth" });
            break;

          case "done":
            streamSucceeded = true;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? { ...m, id: event.assistant_message_id, streaming: false, toolStatus: null }
                  : m,
              ),
            );
            queryClient.invalidateQueries({ queryKey: ["todos"] });
            queryClient.invalidateQueries({ queryKey: ["notes"] });
            break;

          case "error":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? { ...m, content: event.message, streaming: false, toolStatus: null }
                  : m,
              ),
            );
            break;
        }
      }
    } catch (err) {
      let errorText = "Xin lỗi, tôi gặp sự cố. Vui lòng thử lại.";
      if (err instanceof ApiException) {
        if (err.statusCode === 429) {
          errorText = "Bạn đang gửi quá nhiều tin nhắn. Vui lòng đợi một chút.";
        }
      }
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempAssistantId
            ? { ...m, content: errorText, streaming: false, toolStatus: null }
            : m,
        ),
      );
    } finally {
      setIsStreaming(false);
      // Notify parent only after stream ends AND stream succeeded — prevents navigating to
      // a rolled-back conversation_id when LLM errors after meta event
      if (newConvId && streamSucceeded) {
        justCreatedConvIdRef.current = newConvId;
        skipNextHistoryLoadRef.current = true;
        queryClient.invalidateQueries({ queryKey: ["conversations"] });
        onConversationCreated(newConvId);
      } else {
        // Existing conversation — just refresh the sidebar
        queryClient.invalidateQueries({ queryKey: ["conversations"] });
      }
    }
  }

  // Suppress loading spinner for just-created conversations (messages already in state)
  const showHistorySpinner = isLoadingHistory && !skipNextHistoryLoadRef.current;

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
          <p
            className="text-[10px] tracking-[0.15em] flex items-center gap-1.5"
            style={{ color: "#00e676" }}
          >
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-jarvis-success status-online" />
            READY
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {showHistorySpinner ? (
          <div
            className="flex items-center justify-center h-full gap-2"
            style={{ color: "#5e8a9e" }}
          >
            <Loader2 size={16} className="animate-spin" />
            <span
              className="text-xs tracking-widest"
              style={{ fontFamily: "var(--font-orbitron)" }}
            >
              LOADING
            </span>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInput value={input} onChange={setInput} onSend={handleSend} loading={isStreaming} />
    </div>
  );
}
