"use client";

import { useState } from "react";
import { Brain, Plus, Loader2 } from "lucide-react";
import { useMemories, useCreateMemory, useUpdateMemory, useDeleteMemory } from "@/hooks/useMemories";
import type { MemoryOut, MemoryType } from "@/lib/types/api";
import MemoryList from "./MemoryList";
import MemoryEditor from "./MemoryEditor";

export default function MemoryPage() {
  const [typeFilter, setTypeFilter] = useState<MemoryType | "all">("all");
  const [isCreating, setIsCreating] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryOut | null>(null);

  const { data, isLoading, isError, hasNextPage, fetchNextPage, isFetchingNextPage } = useMemories(
    typeFilter === "all" ? undefined : typeFilter,
  );
  const createMemory = useCreateMemory();
  const updateMemory = useUpdateMemory();
  const deleteMemory = useDeleteMemory();

  const memories: MemoryOut[] = data?.pages.flatMap((p) => p.items) ?? [];
  const showEditor = isCreating || editingMemory !== null;
  const isSaving = createMemory.isPending || updateMemory.isPending;

  function handleNew() {
    setEditingMemory(null);
    setIsCreating(true);
  }

  function handleEdit(memory: MemoryOut) {
    setIsCreating(false);
    setEditingMemory(memory);
  }

  function handleCloseEditor() {
    setIsCreating(false);
    setEditingMemory(null);
  }

  async function handleSave(data: {
    content: string;
    memory_type: MemoryType;
    importance: number;
  }) {
    if (isCreating) {
      await createMemory.mutateAsync(data);
      setIsCreating(false);
    } else if (editingMemory) {
      await updateMemory.mutateAsync({ id: editingMemory.id, data });
      setEditingMemory(null);
    }
  }

  function handleDelete(id: string) {
    deleteMemory.mutate(id);
    if (editingMemory?.id === id) setEditingMemory(null);
  }

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "#0b1929" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.12)" }}
      >
        <div className="flex items-center gap-3">
          <Brain size={16} style={{ color: "#00b4d8" }} />
          <h1
            className="text-sm font-bold tracking-[0.25em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            MEMORY
          </h1>
          {memories.length > 0 && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded-full"
              style={{ backgroundColor: "rgba(0,180,216,0.15)", color: "#5e8a9e" }}
            >
              {hasNextPage ? `${memories.length}+` : memories.length}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleNew}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold tracking-[0.12em] transition-all hover:scale-105"
          style={{
            fontFamily: "var(--font-orbitron)",
            background: "linear-gradient(135deg, rgba(0,180,216,0.7), rgba(0,95,138,0.7))",
            color: "#dff3fd",
          }}
        >
          <Plus size={11} />
          MỚI
        </button>
      </div>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Left: list */}
        <div
          className="flex flex-col border-r"
          style={{
            width: showEditor ? "55%" : "100%",
            flexShrink: 0,
            borderColor: "rgba(0,180,216,0.1)",
          }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center flex-1">
              <Loader2 size={18} className="animate-spin" style={{ color: "#5e8a9e" }} />
            </div>
          ) : isError ? (
            <p className="text-center py-8 text-sm" style={{ color: "#ff4444" }}>
              Không tải được. Thử lại.
            </p>
          ) : (
            <MemoryList
              memories={memories}
              typeFilter={typeFilter}
              onTypeFilterChange={setTypeFilter}
              onEdit={handleEdit}
              onDelete={handleDelete}
              hasNextPage={hasNextPage}
              onLoadMore={() => fetchNextPage()}
              isLoadingMore={isFetchingNextPage}
            />
          )}
        </div>

        {/* Right: editor */}
        {showEditor && (
          <div className="flex-1 min-w-0">
            <MemoryEditor
              memory={editingMemory}
              isSaving={isSaving}
              onSave={handleSave}
              onClose={handleCloseEditor}
            />
          </div>
        )}
      </div>
    </div>
  );
}
