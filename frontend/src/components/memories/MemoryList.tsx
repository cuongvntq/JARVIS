"use client";

import { Loader2 } from "lucide-react";
import type { MemoryOut, MemoryType } from "@/lib/types/api";
import MemoryCard from "./MemoryCard";

const FILTERS: { value: MemoryType | "all"; label: string }[] = [
  { value: "all",        label: "Tất cả" },
  { value: "fact",       label: "Sự kiện" },
  { value: "preference", label: "Sở thích" },
  { value: "rule",       label: "Quy tắc" },
  { value: "relation",   label: "Quan hệ" },
  { value: "goal",       label: "Mục tiêu" },
  { value: "other",      label: "Khác" },
];

interface MemoryListProps {
  memories: MemoryOut[];
  typeFilter: MemoryType | "all";
  onTypeFilterChange: (type: MemoryType | "all") => void;
  onEdit: (memory: MemoryOut) => void;
  onDelete: (id: string) => void;
  hasNextPage: boolean | undefined;
  onLoadMore: () => void;
  isLoadingMore: boolean;
}

export default function MemoryList({
  memories,
  typeFilter,
  onTypeFilterChange,
  onEdit,
  onDelete,
  hasNextPage,
  onLoadMore,
  isLoadingMore,
}: MemoryListProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Filter chips */}
      <div
        className="flex flex-wrap gap-1.5 px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.1)" }}
      >
        {FILTERS.map((f) => {
          const isActive = typeFilter === f.value;
          return (
            <button
              key={f.value}
              type="button"
              onClick={() => onTypeFilterChange(f.value)}
              className="px-2.5 py-1 rounded-full text-[10px] font-medium tracking-wide transition-all duration-150"
              style={{
                backgroundColor: isActive ? "rgba(0,180,216,0.18)" : "rgba(0,180,216,0.05)",
                color: isActive ? "#00b4d8" : "#5e8a9e",
                border: isActive ? "1px solid rgba(0,180,216,0.4)" : "1px solid transparent",
              }}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Memory grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {memories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 py-16">
            <p
              className="text-sm text-center"
              style={{ color: "rgba(0,180,216,0.25)", fontFamily: "var(--font-orbitron)", letterSpacing: "0.15em" }}
            >
              CHƯA CÓ MEMORY
            </p>
            <p className="text-xs text-center max-w-xs" style={{ color: "#5e8a9e" }}>
              Chat với JARVIS để tự động ghi nhớ thông tin quan trọng của bạn.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
              {memories.map((m) => (
                <MemoryCard
                  key={m.id}
                  memory={m}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              ))}
            </div>

            {hasNextPage && (
              <div className="flex justify-center mt-4">
                <button
                  type="button"
                  onClick={onLoadMore}
                  disabled={isLoadingMore}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs transition-colors disabled:opacity-50"
                  style={{ color: "#5e8a9e", backgroundColor: "rgba(0,180,216,0.06)" }}
                >
                  {isLoadingMore ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : null}
                  Tải thêm
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
