"use client";

import { Brain } from "lucide-react";

interface MemoryCountProps {
  count: number;
  onNavigate?: (section: string) => void;
}

export default function MemoryCount({ count, onNavigate }: MemoryCountProps) {
  return (
    <button
      type="button"
      onClick={() => onNavigate?.("memory")}
      className="w-full flex items-center justify-between rounded-lg px-4 py-3 transition-all hover:brightness-110 focus:outline-none"
      style={{
        backgroundColor: "rgba(0,230,118,0.06)",
        border: "1px solid rgba(0,230,118,0.10)",
      }}
    >
      <div className="flex items-center gap-2.5">
        <Brain size={14} style={{ color: "#00e676" }} />
        <span
          className="text-[9px] font-semibold tracking-[0.15em]"
          style={{ color: "#00e676", opacity: 0.8 }}
        >
          BỘ NHỚ
        </span>
      </div>
      <span
        className="text-lg font-bold tabular-nums"
        style={{ fontFamily: "var(--font-orbitron)", color: "#00e676" }}
      >
        {count}
      </span>
    </button>
  );
}
