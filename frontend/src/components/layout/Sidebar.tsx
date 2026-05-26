"use client";

import {
  MessageSquare,
  CheckSquare,
  FileText,
  Bell,
  Brain,
  LayoutDashboard,
  Settings,
  Zap,
} from "lucide-react";

export type Section =
  | "chat"
  | "todo"
  | "notes"
  | "reminders"
  | "memory"
  | "dashboard";

interface SidebarProps {
  active: Section;
  onNavigate: (section: Section) => void;
}

const navItems = [
  { id: "chat" as Section, icon: MessageSquare, label: "CHAT" },
  { id: "todo" as Section, icon: CheckSquare, label: "TODO" },
  { id: "notes" as Section, icon: FileText, label: "NOTES" },
  { id: "reminders" as Section, icon: Bell, label: "REMINDERS" },
  { id: "memory" as Section, icon: Brain, label: "MEMORY" },
  { id: "dashboard" as Section, icon: LayoutDashboard, label: "DASHBOARD" },
];

export default function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside
      className="w-[220px] flex-shrink-0 flex flex-col h-full border-r"
      style={{
        backgroundColor: "#060f1c",
        borderColor: "rgba(0, 180, 216, 0.12)",
      }}
    >
      {/* Brand */}
      <div
        className="px-5 py-5 border-b"
        style={{ borderColor: "rgba(0, 180, 216, 0.12)" }}
      >
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
        <div
          className="w-1.5 h-1.5 rounded-full bg-jarvis-success status-online flex-shrink-0"
        />
        <span
          className="text-[9px] tracking-[0.2em] uppercase font-medium"
          style={{ color: "#00e676" }}
        >
          ONLINE
        </span>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150"
              style={{
                backgroundColor: isActive
                  ? "rgba(0, 180, 216, 0.1)"
                  : "transparent",
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
          );
        })}
      </nav>

      {/* Settings */}
      <div
        className="px-3 pb-4 pt-2 border-t"
        style={{ borderColor: "rgba(0, 180, 216, 0.08)" }}
      >
        <button
          type="button"
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 hover:bg-white/5"
          style={{ color: "#5e8a9e" }}
        >
          <Settings size={14} style={{ flexShrink: 0 }} />
          <span
            className="text-[10px] font-semibold tracking-[0.15em]"
            style={{ fontFamily: "var(--font-orbitron)" }}
          >
            SETTINGS
          </span>
        </button>
      </div>
    </aside>
  );
}
