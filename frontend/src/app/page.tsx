"use client";

import ChatInterface from "@/components/chat/ChatInterface";
import DashboardPage from "@/components/dashboard/DashboardPage";
import Sidebar, { type Section } from "@/components/layout/Sidebar";
import MemoryPage from "@/components/memories/MemoryPage";
import NotesPage from "@/components/notes/NotesPage";
import RemindersPage from "@/components/reminders/RemindersPage";
import SettingsPage from "@/components/settings/SettingsPage";
import TodoPage from "@/components/todos/TodoPage";
import { useState } from "react";

function ComingSoon({ name }: { name: string }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <p
          className="text-3xl font-bold tracking-[0.2em]"
          style={{
            fontFamily: "var(--font-orbitron)",
            color: "rgba(0, 180, 216, 0.25)",
          }}
        >
          {name.toUpperCase()}
        </p>
        <div className="w-16 h-px mx-auto" style={{ background: "rgba(0, 180, 216, 0.2)" }} />
        <p className="text-sm" style={{ color: "#5e8a9e" }}>
          Đang phát triển...
        </p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [section, setSection] = useState<Section>("dashboard");
  const [conversationId, setConversationId] = useState<string | null>(null);

  function handleSelectConversation(id: string | null) {
    setConversationId(id);
    setSection("chat");
  }

  return (
    <div className="flex h-full" style={{ backgroundColor: "#030712" }}>
      <Sidebar
        active={section}
        onNavigate={setSection}
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
      />

      <main
        className="flex-1 flex flex-col min-w-0 overflow-hidden"
        style={{ backgroundColor: "#0b1929" }}
      >
        {section === "chat" && (
          <ChatInterface
            conversationId={conversationId}
            onConversationCreated={(id) => setConversationId(id)}
          />
        )}
        {section === "todo" && <TodoPage />}
        {section === "notes" && <NotesPage />}
        {section === "settings" && <SettingsPage />}
        {section === "memory" && <MemoryPage />}
        {section === "reminders" && <RemindersPage />}
        {section === "dashboard" && <DashboardPage onNavigate={setSection} />}
        {section !== "chat" &&
          section !== "todo" &&
          section !== "notes" &&
          section !== "settings" &&
          section !== "memory" &&
          section !== "reminders" &&
          section !== "dashboard" && <ComingSoon name={section} />}
      </main>
    </div>
  );
}
