"use client";

import { useCreateReminder } from "@/hooks/useReminders";
import { cn } from "@/lib/utils";
import { zodResolver } from "@hookform/resolvers/zod";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

const schema = z.object({
  title: z.string().min(1, "Tiêu đề không được trống").max(500),
  remind_at: z.string().min(1, "Thời gian nhắc không được trống"),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface CreateReminderDialogProps {
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

export default function CreateReminderDialog({ open, onClose }: CreateReminderDialogProps) {
  const createReminder = useCreateReminder();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", remind_at: "", description: "" },
  });

  useEffect(() => {
    if (!open) reset();
  }, [open, reset]);

  async function onSubmit(values: FormValues) {
    // Convert datetime-local (local time) → ISO UTC
    const remindDate = new Date(values.remind_at);
    if (remindDate <= new Date()) {
      setError("remind_at", { message: "Thời gian nhắc phải là tương lai" });
      return;
    }

    await createReminder.mutateAsync({
      title: values.title,
      remind_at: remindDate.toISOString(),
      description: values.description || null,
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
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div
        aria-labelledby="create-reminder-title"
        className="w-full max-w-md mx-4 rounded-xl border shadow-2xl"
        style={{ backgroundColor: "#0a1929", borderColor: "rgba(0,180,216,0.25)" }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
          else e.stopPropagation();
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: "rgba(0,180,216,0.12)" }}
        >
          <h2
            id="create-reminder-title"
            className="text-xs font-bold tracking-[0.2em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            TẠO NHẮC NHỞ
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
            <label htmlFor="reminder-title" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              TIÊU ĐỀ *
            </label>
            <input
              id="reminder-title"
              type="text"
              placeholder="Ví dụ: Uống thuốc buổi tối"
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

          {/* Remind at */}
          <div>
            <label htmlFor="reminder-time" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              THỜI GIAN NHẮC *
            </label>
            <input
              id="reminder-time"
              type="datetime-local"
              className={inputCls}
              style={{ ...inputStyle, colorScheme: "dark" }}
              {...register("remind_at")}
            />
            {errors.remind_at && (
              <p className="text-[10px] mt-1" style={{ color: "#ff4444" }}>
                {errors.remind_at.message}
              </p>
            )}
          </div>

          {/* Description */}
          <div>
            <label htmlFor="reminder-desc" className={cn(labelCls)} style={{ color: "#5e8a9e" }}>
              GHI CHÚ <span style={{ color: "rgba(94,138,158,0.5)" }}>(tùy chọn)</span>
            </label>
            <input
              id="reminder-desc"
              type="text"
              placeholder="Chi tiết thêm..."
              className={inputCls}
              style={inputStyle}
              {...register("description")}
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
              disabled={isSubmitting || createReminder.isPending}
              className="flex-1 py-2 rounded-lg text-xs font-semibold tracking-[0.12em] transition-all disabled:opacity-50"
              style={{
                background: "linear-gradient(135deg, rgba(0,180,216,0.8), rgba(0,95,138,0.8))",
                color: "#dff3fd",
              }}
            >
              {createReminder.isPending ? "ĐANG LƯU..." : "TẠO"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
