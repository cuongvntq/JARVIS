"use client";

import { Check, Trash2 } from "lucide-react";
import { formatInTimeZone } from "date-fns-tz";
import { isPast } from "date-fns";
import { cn } from "@/lib/utils";
import type { TodoOut, TodoPriority } from "@/lib/types/api";

interface TodoCardProps {
  todo: TodoOut;
  timezone: string;
  onComplete: (id: string) => void;
  onDelete: (id: string) => void;
  isCompletePending: boolean;
  isDeletePending: boolean;
}

const PRIORITY_STRIP: Record<TodoPriority, string> = {
  low: "bg-jarvis-muted/40",
  medium: "bg-jarvis-accent/60",
  high: "bg-jarvis-warn/70",
  urgent: "bg-jarvis-danger/80",
};

const PRIORITY_LABEL: Record<TodoPriority, string> = {
  low: "THẤP",
  medium: "TB",
  high: "CAO",
  urgent: "KHẨN",
};

const PRIORITY_TEXT: Record<TodoPriority, string> = {
  low: "text-jarvis-muted",
  medium: "text-jarvis-accent",
  high: "text-jarvis-warn",
  urgent: "text-jarvis-danger",
};

export default function TodoCard({
  todo,
  timezone,
  onComplete,
  onDelete,
  isCompletePending,
  isDeletePending,
}: TodoCardProps) {
  const isDone = todo.status === "completed" || todo.status === "cancelled";

  const dueInfo = todo.due_at
    ? {
        text: formatInTimeZone(new Date(todo.due_at), timezone, "HH:mm dd/MM"),
        overdue: !isDone && isPast(new Date(todo.due_at)),
      }
    : null;

  return (
    <div
      className={cn(
        "group flex items-start gap-0 rounded-lg overflow-hidden border transition-all duration-150",
        isDone ? "opacity-50" : "hover:border-jarvis-accent/30",
      )}
      style={{
        backgroundColor: "#0a1a2e",
        borderColor: isDone ? "rgba(94,138,158,0.15)" : "rgba(0,180,216,0.15)",
      }}
    >
      {/* Priority strip */}
      <div className={cn("w-1 self-stretch flex-shrink-0", PRIORITY_STRIP[todo.priority])} />

      {/* Complete button */}
      <button
        type="button"
        onClick={() => onComplete(todo.id)}
        disabled={isDone || isCompletePending}
        className={cn(
          "flex-shrink-0 mt-3 ml-3 w-4 h-4 rounded border flex items-center justify-center transition-colors",
          isDone
            ? "border-jarvis-muted/30 bg-jarvis-muted/20"
            : "border-jarvis-accent/40 hover:border-jarvis-accent hover:bg-jarvis-accent/10",
        )}
      >
        {isDone && <Check size={10} className="text-jarvis-muted" />}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0 px-3 py-3">
        <p
          className={cn("text-sm leading-snug break-words", isDone && "line-through")}
          style={{ color: isDone ? "#5e8a9e" : "#dff3fd" }}
        >
          {todo.title}
        </p>

        {todo.description && (
          <p className="text-xs mt-0.5 truncate" style={{ color: "#4a7a8e" }}>
            {todo.description}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5">
          {/* Priority badge */}
          <span className={cn("text-[9px] font-semibold tracking-[0.1em]", PRIORITY_TEXT[todo.priority])}>
            {PRIORITY_LABEL[todo.priority]}
          </span>

          {/* Due date */}
          {dueInfo && (
            <span
              className="text-[10px]"
              style={{ color: dueInfo.overdue ? "#ff4444" : "#5e8a9e" }}
            >
              {dueInfo.overdue ? "⚠ " : ""}
              {dueInfo.text}
            </span>
          )}

          {/* Tags */}
          {todo.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-[9px] px-1.5 py-0.5 rounded"
              style={{ backgroundColor: "rgba(0,180,216,0.08)", color: "#5e8a9e" }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Delete */}
      <button
        type="button"
        onClick={() => onDelete(todo.id)}
        disabled={isDeletePending}
        className="flex-shrink-0 mt-3 mr-3 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:text-jarvis-danger"
        style={{ color: "#3a6a7e" }}
      >
        <Trash2 size={12} />
      </button>
    </div>
  );
}
