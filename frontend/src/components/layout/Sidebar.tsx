"use client";

import { useConversations } from "@/hooks/useConversations";
import { useAuthStore } from "@/stores/authStore";
import {
  Bell,
  Brain,
  CheckSquare,
  FileText,
  LayoutDashboard,
  Loader2,
  LogOut,
  MessageSquare,
  Plus,
  Settings,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export type Section = "chat" | "todo" | "notes" | "reminders" | "memory" | "dashboard" | "settings";

interface SidebarProps {
  active: Section;
  onNavigate: (section: Section) => void;
  activeConversationId: string | null;
  onSelectConversation: (id: string | null) => void;
}

const navItems = [
  { id: "chat" as Section, icon: MessageSquare, label: "CHAT" },
  { id: "todo" as Section, icon: CheckSquare, label: "TODO" },
  { id: "notes" as Section, icon: FileText, label: "NOTES" },
  { id: "reminders" as Section, icon: Bell, label: "REMINDERS" },
  { id: "memory" as Section, icon: Brain, label: "MEMORY" },
  { id: "dashboard" as Section, icon: LayoutDashboard, label: "DASHBOARD" },
];

function ConversationList({
  activeId,
  onSelect,
}: {
  activeId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const { data, isLoading } = useConversations();
  const conversations = data?.items ?? [];

  return (
    <div className="mt-1 mb-2">
      {/* New Chat button */}
      <button
        type="button"
        onClick={() => onSelect(null)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-150 hover:bg-white/5"
        style={{ color: activeId === null ? "#00b4d8" : "#5e8a9e" }}
      >
        <Plus size={12} style={{ flexShrink: 0 }} />
        <span
          className="text-[9px] font-semibold tracking-[0.12em]"
          style={{
            fontFamily: "var(--font-orbitron)",
            color: activeId === null ? "#00b4d8" : "#5e8a9e",
          }}
        >
          NEW CHAT
        </span>
      </button>

      {/* Conversation list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-3">
          <Loader2 size={12} className="animate-spin" style={{ color: "#5e8a9e" }} />
        </div>
      ) : conversations.length === 0 ? (
        <p
          className="px-3 py-1.5 text-[9px] tracking-[0.1em]"
          style={{ color: "rgba(0, 180, 216, 0.3)" }}
        >
          Chưa có hội thoại nào
        </p>
      ) : (
        <div className="space-y-0.5 max-h-[220px] overflow-y-auto">
          {conversations.map((conv) => {
            const isActive = conv.id === activeId;
            return (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelect(conv.id)}
                className="w-full text-left px-3 py-1.5 rounded-lg transition-all duration-150 truncate"
                style={{
                  backgroundColor: isActive ? "rgba(0, 180, 216, 0.08)" : "transparent",
                  borderLeft: isActive
                    ? "2px solid rgba(0, 180, 216, 0.5)"
                    : "2px solid transparent",
                  color: isActive ? "#dff3fd" : "#4a7a8e",
                  fontSize: "10px",
                  letterSpacing: "0.02em",
                }}
              >
                {conv.title}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Sidebar({
  active,
  onNavigate,
  activeConversationId,
  onSelectConversation,
}: SidebarProps) {
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    await logout();
    router.push("/auth/login");
  };

  return (
    <aside
      className="w-[220px] flex-shrink-0 flex flex-col h-full border-r"
      style={{
        backgroundColor: "#060f1c",
        borderColor: "rgba(0, 180, 216, 0.12)",
      }}
    >
      {/* Brand */}
      <div className="px-5 py-5 border-b" style={{ borderColor: "rgba(0, 180, 216, 0.12)" }}>
        <div className="flex items-center gap-2.5 mb-1.5">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            style={{
              background:
                "radial-gradient(circle, rgba(0, 180, 216, 0.7) 0%, rgba(0, 95, 138, 0.4) 100%)",
              boxShadow: "0 0 14px rgba(0, 180, 216, 0.45)",
            }}
          >
            <Zap size={15} className="text-white" />
          </div>
          <h1
            className="text-base font-bold tracking-[0.2em] text-jarvis-accent"
            style={{
              fontFamily: "var(--font-orbitron)",
              textShadow: "0 0 14px rgba(0, 180, 216, 0.5)",
            }}
          >
            JARVIS
          </h1>
        </div>
        <p
          className="text-[9px] tracking-[0.2em] uppercase pl-10"
          style={{ color: "rgba(0, 180, 216, 0.4)" }}
        >
          Personal AI · v0.1
        </p>
      </div>

      {/* Status */}
      <div
        className="px-5 py-2.5 border-b flex items-center gap-2"
        style={{ borderColor: "rgba(0, 180, 216, 0.08)" }}
      >
        <div className="w-1.5 h-1.5 rounded-full bg-jarvis-success status-online flex-shrink-0" />
        <span
          className="text-[9px] tracking-[0.2em] uppercase font-medium"
          style={{ color: "#00e676" }}
        >
          ONLINE
        </span>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-3 py-3 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <div key={item.id}>
              <button
                type="button"
                onClick={() => onNavigate(item.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150"
                style={{
                  backgroundColor: isActive ? "rgba(0, 180, 216, 0.1)" : "transparent",
                  borderLeft: isActive
                    ? "2px solid rgba(0, 180, 216, 0.7)"
                    : "2px solid transparent",
                }}
              >
                <Icon
                  size={14}
                  style={{
                    color: isActive ? "#00b4d8" : "#5e8a9e",
                    flexShrink: 0,
                  }}
                />
                <span
                  className="text-[10px] font-semibold tracking-[0.15em]"
                  style={{
                    fontFamily: "var(--font-orbitron)",
                    color: isActive ? "#dff3fd" : "#5e8a9e",
                  }}
                >
                  {item.label}
                </span>
              </button>

              {/* Conversation list — only under CHAT when active */}
              {item.id === "chat" && isActive && (
                <ConversationList activeId={activeConversationId} onSelect={onSelectConversation} />
              )}
            </div>
          );
        })}
      </nav>

      {/* Settings + Logout */}
      <div className="px-3 pb-3 pt-2 border-t" style={{ borderColor: "rgba(0, 180, 216, 0.08)" }}>
        <button
          type="button"
          onClick={() => onNavigate("settings")}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150"
          style={{
            backgroundColor: active === "settings" ? "rgba(0, 180, 216, 0.1)" : "transparent",
            borderLeft:
              active === "settings" ? "2px solid rgba(0, 180, 216, 0.7)" : "2px solid transparent",
          }}
        >
          <Settings
            size={14}
            style={{ color: active === "settings" ? "#00b4d8" : "#5e8a9e", flexShrink: 0 }}
          />
          <span
            className="text-[10px] font-semibold tracking-[0.15em]"
            style={{
              fontFamily: "var(--font-orbitron)",
              color: active === "settings" ? "#dff3fd" : "#5e8a9e",
            }}
          >
            SETTINGS
          </span>
        </button>

        {/* User info + logout */}
        <div
          className="mt-2 px-3 py-2 rounded-lg flex items-center gap-2"
          style={{ backgroundColor: "rgba(0, 180, 216, 0.04)" }}
        >
          <div className="flex-1 min-w-0">
            <p
              className="text-[9px] font-semibold tracking-[0.1em] truncate"
              style={{ color: "#5e8a9e" }}
            >
              {user?.name ?? "USER"}
            </p>
            <p
              className="text-[8px] tracking-[0.05em] truncate"
              style={{ color: "rgba(94, 138, 158, 0.6)" }}
            >
              {user?.email ?? ""}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            title="Logout"
            className="flex-shrink-0 p-1 rounded transition-colors hover:bg-white/5 disabled:opacity-50"
          >
            {isLoggingOut ? (
              <Loader2 size={12} className="animate-spin" style={{ color: "#5e8a9e" }} />
            ) : (
              <LogOut size={12} style={{ color: "#5e8a9e" }} />
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
