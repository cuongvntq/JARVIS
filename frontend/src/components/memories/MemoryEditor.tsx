"use client";

import type { MemoryOut, MemoryType } from "@/lib/types/api";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

const TYPE_OPTIONS: { value: MemoryType; label: string }[] = [
  { value: "fact", label: "Sự kiện" },
  { value: "preference", label: "Sở thích" },
  { value: "rule", label: "Quy tắc" },
  { value: "relation", label: "Quan hệ" },
  { value: "goal", label: "Mục tiêu" },
  { value: "other", label: "Khác" },
];

interface MemoryEditorProps {
  memory: MemoryOut | null;
  isSaving: boolean;
  onSave: (data: { content: string; memory_type: MemoryType; importance: number }) => Promise<void>;
  onClose: () => void;
}

export default function MemoryEditor({ memory, isSaving, onSave, onClose }: MemoryEditorProps) {
  const [content, setContent] = useState("");
  const [memoryType, setMemoryType] = useState<MemoryType>("fact");
  const [importance, setImportance] = useState(5);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (memory) {
      setContent(memory.content);
      setMemoryType(memory.memory_type as MemoryType);
      setImportance(memory.importance);
    } else {
      setContent("");
      setMemoryType("fact");
      setImportance(5);
    }
    setValidationError(null);
  }, [memory]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) {
      setValidationError("Nội dung không được để trống");
      return;
    }
    try {
      await onSave({ content: content.trim(), memory_type: memoryType, importance });
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : "Không thể lưu, thử lại sau");
    }
  }

  const inputStyle = {
    backgroundColor: "#0b1929",
    border: "1px solid rgba(0,180,216,0.2)",
    color: "#dff3fd",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Editor header */}
      <div
        className="flex items-center justify-between px-5 py-3.5 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.1)" }}
      >
        <span
          className="text-[10px] font-semibold tracking-[0.2em] uppercase"
          style={{ fontFamily: "var(--font-orbitron)", color: "#5e8a9e" }}
        >
          {memory ? "Sửa memory" : "Memory mới"}
        </span>
        <button
          type="button"
          onClick={onClose}
          disabled={isSaving}
          className="p-1 rounded hover:bg-white/5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <X size={14} style={{ color: "#5e8a9e" }} />
        </button>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-y-auto p-5 gap-5">
        {/* Content */}
        <div className="space-y-1.5">
          <label
            htmlFor="memory-content"
            className="block text-xs tracking-wide"
            style={{ color: "#5e8a9e" }}
          >
            Nội dung
          </label>
          <textarea
            id="memory-content"
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setValidationError(null);
            }}
            disabled={isSaving}
            rows={6}
            maxLength={2000}
            placeholder="Nhập thông tin cần ghi nhớ..."
            className="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none transition-colors focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ ...inputStyle, ["--tw-ring-color" as string]: "rgba(0,180,216,0.4)" }}
          />
          <div className="flex justify-between">
            {validationError ? (
              <p className="text-[10px]" style={{ color: "#ff4444" }}>
                {validationError}
              </p>
            ) : (
              <span />
            )}
            <p className="text-[10px]" style={{ color: "rgba(94,138,158,0.5)" }}>
              {content.length}/2000
            </p>
          </div>
        </div>

        {/* Type */}
        <div className="space-y-1.5">
          <label
            htmlFor="memory-type"
            className="block text-xs tracking-wide"
            style={{ color: "#5e8a9e" }}
          >
            Loại
          </label>
          <select
            id="memory-type"
            value={memoryType}
            onChange={(e) => setMemoryType(e.target.value as MemoryType)}
            disabled={isSaving}
            className="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ ...inputStyle, ["--tw-ring-color" as string]: "rgba(0,180,216,0.4)" }}
          >
            {TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} style={{ backgroundColor: "#0b1929" }}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Importance slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label
              htmlFor="memory-importance"
              className="block text-xs tracking-wide"
              style={{ color: "#5e8a9e" }}
            >
              Mức độ quan trọng
            </label>
            <span
              className="text-xs font-semibold px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: "rgba(0,180,216,0.12)",
                color: "#00b4d8",
              }}
            >
              {importance}/10
            </span>
          </div>
          <input
            id="memory-importance"
            type="range"
            min={1}
            max={10}
            value={importance}
            onChange={(e) => setImportance(Number(e.target.value))}
            disabled={isSaving}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ accentColor: "#00b4d8" }}
          />
          <div
            className="flex justify-between text-[9px]"
            style={{ color: "rgba(94,138,158,0.5)" }}
          >
            <span>Thấp</span>
            <span>Cao</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2 mt-auto">
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="flex-1 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all disabled:opacity-50"
            style={{
              backgroundColor: "rgba(94,138,158,0.1)",
              color: "#5e8a9e",
              border: "1px solid rgba(94,138,158,0.2)",
            }}
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="flex-1 py-2 rounded-lg text-xs font-semibold tracking-[0.1em] uppercase transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              fontFamily: "var(--font-orbitron)",
              background: "linear-gradient(135deg, rgba(0,180,216,0.8), rgba(0,95,138,0.8))",
              color: "#dff3fd",
              border: "1px solid rgba(0,180,216,0.3)",
            }}
          >
            {isSaving ? "Đang lưu..." : "Lưu"}
          </button>
        </div>
      </form>
    </div>
  );
}
