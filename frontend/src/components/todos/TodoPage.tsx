"use client";

import { useCompleteTodo, useDeleteTodo, useTodos } from "@/hooks/useTodos";
import type { TodoFilter } from "@/lib/types/api";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import { CheckSquare, Loader2, Plus } from "lucide-react";
import { useState } from "react";
import CreateTodoDialog from "./CreateTodoDialog";
import TodoCard from "./TodoCard";

const FILTERS: { id: TodoFilter; label: string }[] = [
  { id: "today", label: "HÔM NAY" },
  { id: "upcoming", label: "SẮP TỚI" },
  { id: "overdue", label: "QUÁ HẠN" },
  { id: "completed", label: "XONG" },
  { id: "all", label: "TẤT CẢ" },
];

export default function TodoPage() {
  const [filter, setFilter] = useState<TodoFilter>("all");
  const [dialogOpen, setDialogOpen] = useState(false);

  const user = useAuthStore((s) => s.user);
  const timezone = user?.timezone ?? "UTC";

  const { data, isLoading, isError, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useTodos(filter);
  const completeTodo = useCompleteTodo();
  const deleteTodo = useDeleteTodo();

  const todos = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "#0b1929" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.12)" }}
      >
        <div className="flex items-center gap-3">
          <CheckSquare size={16} style={{ color: "#00b4d8" }} />
          <h1
            className="text-sm font-bold tracking-[0.25em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            TODOS
          </h1>
          {todos.length > 0 && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded-full"
              style={{ backgroundColor: "rgba(0,180,216,0.15)", color: "#5e8a9e" }}
            >
              {hasNextPage ? `${todos.length}+` : todos.length}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold tracking-[0.12em] transition-all hover:scale-105"
          style={{
            background: "linear-gradient(135deg, rgba(0,180,216,0.7), rgba(0,95,138,0.7))",
            color: "#dff3fd",
          }}
        >
          <Plus size={11} />
          MỚI
        </button>
      </div>

      {/* Filter tabs */}
      <div
        className="flex items-center gap-1 px-6 py-2.5 border-b flex-shrink-0 overflow-x-auto"
        style={{ borderColor: "rgba(0,180,216,0.08)" }}
      >
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={cn(
              "px-3 py-1 rounded text-[9px] font-semibold tracking-[0.12em] transition-all whitespace-nowrap",
              filter === f.id ? "text-jarvis-accent" : "text-jarvis-muted hover:text-jarvis-fg",
            )}
            style={{
              backgroundColor: filter === f.id ? "rgba(0,180,216,0.12)" : "transparent",
              borderBottom:
                filter === f.id ? "1px solid rgba(0,180,216,0.6)" : "1px solid transparent",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Todo list */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={18} className="animate-spin" style={{ color: "#5e8a9e" }} />
          </div>
        )}

        {isError && (
          <p className="text-center py-16 text-sm" style={{ color: "#ff4444" }}>
            Không tải được danh sách. Thử lại sau.
          </p>
        )}

        {!isLoading && !isError && todos.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <CheckSquare size={28} style={{ color: "rgba(0,180,216,0.2)" }} />
            <p className="text-sm tracking-[0.1em]" style={{ color: "rgba(0,180,216,0.3)" }}>
              {filter === "today"
                ? "Không có việc nào hôm nay"
                : filter === "overdue"
                  ? "Không có việc quá hạn"
                  : filter === "completed"
                    ? "Chưa hoàn thành việc nào"
                    : "Chưa có việc nào"}
            </p>
            {filter === "all" && (
              <button
                type="button"
                onClick={() => setDialogOpen(true)}
                className="text-[10px] tracking-[0.1em] transition-colors hover:text-jarvis-accent"
                style={{ color: "#5e8a9e" }}
              >
                + Tạo việc đầu tiên
              </button>
            )}
          </div>
        )}

        {!isLoading && !isError && todos.length > 0 && (
          <div className="space-y-2">
            {todos.map((todo) => (
              <TodoCard
                key={todo.id}
                todo={todo}
                timezone={timezone}
                onComplete={(id) => completeTodo.mutate(id)}
                onDelete={(id) => deleteTodo.mutate(id)}
                isCompletePending={completeTodo.isPending}
                isDeletePending={deleteTodo.isPending}
              />
            ))}
            {hasNextPage && (
              <div className="flex justify-center pt-2 pb-1">
                <button
                  type="button"
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                  className="px-4 py-1.5 rounded-lg border text-[10px] tracking-[0.1em] transition-colors hover:border-jarvis-accent/30 hover:text-jarvis-accent disabled:opacity-50"
                  style={{ color: "#5e8a9e", borderColor: "rgba(94,138,158,0.2)" }}
                >
                  {isFetchingNextPage ? "Đang tải..." : "Tải thêm"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <CreateTodoDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
}
