"use client";

import {
  useCreateMemory,
  useDeleteMemory,
  useMemories,
  useUpdateMemory,
} from "@/hooks/useMemories";
import type { MemoryOut, MemoryType } from "@/lib/types/api";
import { Brain, Loader2, Plus } from "lucide-react";
import { useState } from "react";
import MemoryEditor from "./MemoryEditor";
import MemoryList from "./MemoryList";

type EditorState = { mode: "closed" } | { mode: "create" } | { mode: "edit"; memory: MemoryOut };

export default function MemoryPage() {
  const [typeFilter, setTypeFilter] = useState<MemoryType | "all">("all");
  const [editor, setEditor] = useState<EditorState>({ mode: "closed" });

  const { data, isLoading, isError, hasNextPage, fetchNextPage, isFetchingNextPage } = useMemories(
    typeFilter === "all" ? undefined : typeFilter,
  );
  const createMemory = useCreateMemory();
  const updateMemory = useUpdateMemory();
  const deleteMemory = useDeleteMemory();

  const memories: MemoryOut[] = data?.pages.flatMap((p) => p.items) ?? [];
  const showEditor = editor.mode !== "closed";
  const isSaving = createMemory.isPending || updateMemory.isPending;

  function handleNew() {
    if (isSaving) return;
    setEditor({ mode: "create" });
  }

  function handleEdit(memory: MemoryOut) {
    if (isSaving) return;
    setEditor({ mode: "edit", memory });
  }

  function handleCloseEditor() {
    if (isSaving) return;
    setEditor({ mode: "closed" });
  }

  async function handleSave(data: {
    content: string;
    memory_type: MemoryType;
    importance: number;
  }) {
    if (editor.mode === "create") {
      await createMemory.mutateAsync(data);
      setEditor({ mode: "closed" });
    } else if (editor.mode === "edit") {
      await updateMemory.mutateAsync({ id: editor.memory.id, data });
      setEditor({ mode: "closed" });
    }
  }

  function handleDelete(id: string) {
    if (isSaving) return;
    deleteMemory.mutate(id);
    if (editor.mode === "edit" && editor.memory.id === id) {
      setEditor({ mode: "closed" });
    }
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
          disabled={isSaving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold tracking-[0.12em] transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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
              isSaving={isSaving}
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
              memory={editor.mode === "edit" ? editor.memory : null}
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
