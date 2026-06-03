"use client";

import type { MemoryOut, MemoryType } from "@/lib/types/api";
import { Pencil, Trash2 } from "lucide-react";

const TYPE_META: Record<MemoryType, { label: string; color: string; bg: string }> = {
  fact: { label: "Sự kiện", color: "#00b4d8", bg: "rgba(0,180,216,0.12)" },
  preference: { label: "Sở thích", color: "#a78bfa", bg: "rgba(167,139,250,0.12)" },
  rule: { label: "Quy tắc", color: "#fb923c", bg: "rgba(251,146,60,0.12)" },
  relation: { label: "Quan hệ", color: "#34d399", bg: "rgba(52,211,153,0.12)" },
  goal: { label: "Mục tiêu", color: "#fbbf24", bg: "rgba(251,191,36,0.12)" },
  other: { label: "Khác", color: "#5e8a9e", bg: "rgba(94,138,158,0.12)" },
};

interface MemoryCardProps {
  memory: MemoryOut;
  onEdit: (memory: MemoryOut) => void;
  onDelete: (id: string) => void;
  isSaving: boolean;
}

export default function MemoryCard({ memory, onEdit, onDelete, isSaving }: MemoryCardProps) {
  const meta = TYPE_META[memory.memory_type as MemoryType] ?? TYPE_META.other;

  return (
    <div
      className="group relative rounded-xl p-4 transition-all duration-150 hover:ring-1"
      style={{
        backgroundColor: "#0f2235",
        border: "1px solid rgba(0,180,216,0.1)",
        ["--tw-ring-color" as string]: "rgba(0,180,216,0.25)",
      }}
    >
      {/* Top row: type badge + importance + actions */}
      <div className="flex items-center justify-between mb-2.5">
        <span
          className="text-[9px] font-semibold tracking-[0.15em] uppercase px-2 py-0.5 rounded-full"
          style={{ color: meta.color, backgroundColor: meta.bg }}
        >
          {meta.label}
        </span>

        <div className="flex items-center gap-2">
          {/* Importance dots */}
          <div className="flex items-center gap-0.5">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((dot) => (
              <div
                key={`dot-${dot}`}
                className="w-1 h-1 rounded-full"
                style={{
                  backgroundColor: dot <= memory.importance ? meta.color : "rgba(94,138,158,0.2)",
                }}
              />
            ))}
          </div>

          {/* Action buttons (visible on hover) */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            <button
              type="button"
              onClick={() => onEdit(memory)}
              disabled={isSaving}
              className="p-1 rounded transition-colors hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
              title="Sửa"
            >
              <Pencil size={11} style={{ color: "#5e8a9e" }} />
            </button>
            <button
              type="button"
              onClick={() => onDelete(memory.id)}
              disabled={isSaving}
              className="p-1 rounded transition-colors hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
              title="Xóa"
            >
              <Trash2 size={11} style={{ color: "#ff4444" }} />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <p className="text-sm leading-relaxed line-clamp-4" style={{ color: "#dff3fd" }}>
        {memory.content}
      </p>
    </div>
  );
}
