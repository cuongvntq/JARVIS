"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCreateTodo } from "@/hooks/useTodos";

const schema = z.object({
  title: z.string().min(1, "Tiêu đề không được trống").max(500),
  priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
  due_at: z.string().optional(),
  tags: z.string().default(""),
});

type FormValues = z.infer<typeof schema>;

interface CreateTodoDialogProps {
  open: boolean;
  onClose: () => void;
}

const inputCls =
  "w-full px-3 py-2 rounded-lg text-sm bg-transparent border focus:outline-none transition-colors";
const inputStyle = {
  borderColor: "rgba(0,180,216,0.25)",
  color: "#dff3fd",
  backgroundColor: "rgba(0,20,40,0.6)",
};

const labelCls = "block text-[10px] font-semibold tracking-[0.12em] mb-1.5";

export default function CreateTodoDialog({ open, onClose }: CreateTodoDialogProps) {
  const createTodo = useCreateTodo();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", priority: "medium", due_at: "", tags: "" },
  });

  useEffect(() => {
    if (!open) reset();
  }, [open, reset]);

  async function onSubmit(values: FormValues) {
    const tags = values.tags
      ? values.tags.split(",").map((t) => t.trim()).filter(Boolean)
      : [];

    const due_at =
      values.due_at && values.due_at.length > 0
        ? new Date(values.due_at).toISOString()
        : undefined;

    await createTodo.mutateAsync({
      title: values.title,
      priority: values.priority,
      due_at: due_at ?? null,
      tags,
      source: "ui",
    });

    onClose();
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "rgba(0,0,0,0.7)" }}
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        aria-labelledby="create-todo-title"
        className="w-full max-w-md mx-4 rounded-xl border shadow-2xl"
        style={{
          backgroundColor: "#0a1929",
          borderColor: "rgba(0,180,216,0.25)",
        }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: "rgba(0,180,216,0.12)" }}
        >
          <h2
            id="create-todo-title"
            className="text-xs font-bold tracking-[0.2em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            TẠO VIỆC MỚI
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-white/5 transition-colors"
            style={{ color: "#5e8a9e" }}
          >
            <X size={14} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="px-5 py-4 space-y-4">
          {/* Title */}
          <div>
            <label htmlFor="todo-title" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              TIÊU ĐỀ *
            </label>
            <input
              id="todo-title"
              type="text"
              placeholder="Ví dụ: Mua sữa chiều nay"
              className={inputCls}
              style={inputStyle}
              {...register("title")}
            />
            {errors.title && (
              <p className="text-[10px] mt-1" style={{ color: "#ff4444" }}>
                {errors.title.message}
              </p>
            )}
          </div>

          {/* Priority */}
          <div>
            <label htmlFor="todo-priority" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              ƯU TIÊN
            </label>
            <select
              id="todo-priority"
              className={cn(inputCls, "cursor-pointer")}
              style={{ ...inputStyle }}
              {...register("priority")}
            >
              <option value="low">Thấp</option>
              <option value="medium">Trung bình</option>
              <option value="high">Cao</option>
              <option value="urgent">Khẩn cấp</option>
            </select>
          </div>

          {/* Due date */}
          <div>
            <label htmlFor="todo-due" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              THỜI HẠN
            </label>
            <input
              id="todo-due"
              type="datetime-local"
              className={inputCls}
              style={{ ...inputStyle, colorScheme: "dark" }}
              {...register("due_at")}
            />
          </div>

          {/* Tags */}
          <div>
            <label htmlFor="todo-tags" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              NHÃN <span style={{ color: "rgba(94,138,158,0.5)" }}>(phân cách bằng dấu phẩy)</span>
            </label>
            <input
              id="todo-tags"
              type="text"
              placeholder="công việc, cá nhân, mua sắm"
              className={inputCls}
              style={inputStyle}
              {...register("tags")}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg text-xs font-semibold tracking-[0.12em] border transition-colors hover:bg-white/5"
              style={{ borderColor: "rgba(94,138,158,0.3)", color: "#5e8a9e" }}
            >
              HỦY
            </button>
            <button
              type="submit"
              disabled={isSubmitting || createTodo.isPending}
              className="flex-1 py-2 rounded-lg text-xs font-semibold tracking-[0.12em] transition-all disabled:opacity-50"
              style={{
                background: "linear-gradient(135deg, rgba(0,180,216,0.8), rgba(0,95,138,0.8))",
                color: "#dff3fd",
              }}
            >
              {createTodo.isPending ? "ĐANG LƯU..." : "TẠO"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
