"use client";

import { useEffect, useState } from "react";
import { Save, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NoteOut } from "@/lib/types/api";

interface NoteEditorProps {
  note: NoteOut | null;
  isSaving: boolean;
  onSave: (data: { title: string; content: string; tags: string[] }) => Promise<void>;
  onClose: () => void;
}

const inputBase =
  "w-full bg-transparent focus:outline-none transition-colors";

export default function NoteEditor({ note, isSaving, onSave, onClose }: NoteEditorProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  // Re-initialize only when the selected note id changes, not on every
  // refetch of the same note — this preserves unsaved drafts across
  // React Query invalidations (focus, chat mutation, pin/delete another note).
  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional dep on id only
  useEffect(() => {
    setTitle(note?.title ?? "");
    setContent(note?.content ?? "");
    setTagsInput(note?.tags.join(", ") ?? "");
    setValidationError(null);
  }, [note?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const isDirty =
    title !== (note?.title ?? "") ||
    content !== (note?.content ?? "") ||
    tagsInput !== (note?.tags.join(", ") ?? "");

  async function handleSave() {
    if (!title.trim()) return;
    const normalizedTitle = title.trim();
    const tags = tagsInput
      ? tagsInput.split(",").map((t) => t.trim()).filter(Boolean)
      : [];
    try {
      await onSave({ title: normalizedTitle, content, tags });
      // Sync normalized values back so isDirty is accurate after save —
      // without this, raw input (" hello", "a,b") stays in local state while
      // the server stores the trimmed form, keeping the Save button visible.
      setTitle(normalizedTitle);
      setTagsInput(tags.join(", "));
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : "Không thể lưu, thử lại sau");
    }
  }

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "#0b1929" }}>
      {/* Toolbar */}
      <div
        className="flex items-center justify-between px-5 py-3 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.1)" }}
      >
        <span
          className="text-[9px] tracking-[0.15em]"
          style={{ color: "rgba(0,180,216,0.4)" }}
        >
          {note ? "CHỈNH SỬA GHI CHÚ" : "GHI CHÚ MỚI"}
        </span>

        <div className="flex items-center gap-2">
          {isDirty && (
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !title.trim()}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded text-[9px] font-semibold tracking-[0.1em] transition-all",
                "disabled:opacity-50",
              )}
              style={{
                background: "linear-gradient(135deg, rgba(0,180,216,0.7), rgba(0,95,138,0.7))",
                color: "#dff3fd",
              }}
            >
              <Save size={10} />
              {isSaving ? "ĐANG LƯU..." : "LƯU"}
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            disabled={isSaving}
            className="p-1 rounded hover:bg-white/5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            style={{ color: "#5e8a9e" }}
          >
            <X size={12} />
          </button>
        </div>
      </div>

      {/* Error bar */}
      {validationError && (
        <div
          className="px-5 py-2 text-[10px] flex-shrink-0"
          style={{ backgroundColor: "rgba(255,68,68,0.08)", color: "#ff4444", borderBottom: "1px solid rgba(255,68,68,0.2)" }}
        >
          {validationError}
        </div>
      )}

      {/* Editor area */}
      <div className="flex-1 flex flex-col overflow-hidden px-6 py-4 gap-3">
        {/* Title */}
        <input
          type="text"
          value={title}
          onChange={(e) => { setTitle(e.target.value); setValidationError(null); }}
          placeholder="Tiêu đề ghi chú..."
          className={cn(inputBase, "text-lg font-semibold")}
          style={{ color: "#dff3fd" }}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.preventDefault();
          }}
        />

        {/* Divider */}
        <div style={{ height: "1px", backgroundColor: "rgba(0,180,216,0.1)" }} />

        {/* Content */}
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Nội dung ghi chú... (markdown hỗ trợ)"
          className={cn(inputBase, "flex-1 resize-none text-sm leading-relaxed")}
          style={{ color: "#c0dde8", minHeight: 0 }}
        />

        {/* Tags */}
        <div
          className="flex items-center gap-2 pt-2 border-t"
          style={{ borderColor: "rgba(0,180,216,0.08)" }}
        >
          <span
            className="text-[9px] font-semibold tracking-[0.12em] flex-shrink-0"
            style={{ color: "#5e8a9e" }}
          >
            NHÃN:
          </span>
          <input
            type="text"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="tag1, tag2, tag3"
            className={cn(inputBase, "text-[11px]")}
            style={{ color: "#5e8a9e" }}
          />
        </div>
      </div>
    </div>
  );
}
