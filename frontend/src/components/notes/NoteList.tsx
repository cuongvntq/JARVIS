"use client";

import { Search, Pin, Trash2, PinOff } from "lucide-react";
import { formatInTimeZone } from "date-fns-tz";
import { cn } from "@/lib/utils";
import type { NoteOut } from "@/lib/types/api";

interface NoteListProps {
  notes: NoteOut[];
  selectedId: string | null;
  timezone: string;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSelect: (id: string) => void;
  onPin: (id: string, pinned: boolean) => void;
  onDelete: (id: string) => void;
}

function NoteItem({
  note,
  selected,
  timezone,
  onSelect,
  onPin,
  onDelete,
}: {
  note: NoteOut;
  selected: boolean;
  timezone: string;
  onSelect: () => void;
  onPin: () => void;
  onDelete: () => void;
}) {
  const updatedAt = formatInTimeZone(
    new Date(note.updated_at),
    timezone,
    "dd/MM HH:mm",
  );

  return (
    <div
      className={cn(
        "group flex items-start rounded-lg transition-all duration-150 border",
        selected
          ? "border-jarvis-accent/30"
          : "border-transparent hover:border-jarvis-accent/15",
      )}
      style={{
        backgroundColor: selected ? "rgba(0,180,216,0.07)" : "transparent",
      }}
    >
      {/* Main clickable area */}
      <button
        type="button"
        onClick={onSelect}
        className="flex-1 min-w-0 text-left px-3 py-2.5"
      >
        <div className="flex items-start justify-between gap-1">
          <p
            className="text-[11px] font-medium leading-snug truncate"
            style={{ color: selected ? "#dff3fd" : "#a0c8da" }}
          >
            {note.title || "Không có tiêu đề"}
          </p>
          {note.pinned && (
            <Pin size={9} className="flex-shrink-0 mt-0.5" style={{ color: "#00b4d8" }} />
          )}
        </div>
        {note.content && (
          <p
            className="text-[10px] mt-0.5 line-clamp-1 text-left"
            style={{ color: "#4a7a8e" }}
          >
            {note.content}
          </p>
        )}
        <p className="text-[9px] mt-1 text-left" style={{ color: "rgba(94,138,158,0.5)" }}>
          {updatedAt}
        </p>
      </button>

      {/* Action buttons */}
      <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 py-2.5 pr-2">
        <button
          type="button"
          onClick={onPin}
          className="p-0.5 rounded hover:text-jarvis-accent transition-colors"
          style={{ color: "#3a6a7e" }}
          title={note.pinned ? "Bỏ ghim" : "Ghim"}
        >
          {note.pinned ? <PinOff size={10} /> : <Pin size={10} />}
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="p-0.5 rounded hover:text-jarvis-danger transition-colors"
          style={{ color: "#3a6a7e" }}
          title="Xóa"
        >
          <Trash2 size={10} />
        </button>
      </div>
    </div>
  );
}

export default function NoteList({
  notes,
  selectedId,
  timezone,
  searchQuery,
  onSearchChange,
  onSelect,
  onPin,
  onDelete,
}: NoteListProps) {
  const pinned = notes.filter((n) => n.pinned);
  const unpinned = notes.filter((n) => !n.pinned);

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div
        className="px-3 py-3 border-b"
        style={{ borderColor: "rgba(0,180,216,0.08)" }}
      >
        <div
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border"
          style={{
            borderColor: "rgba(0,180,216,0.2)",
            backgroundColor: "rgba(0,20,40,0.5)",
          }}
        >
          <Search size={11} style={{ color: "#5e8a9e", flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Tìm ghi chú..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="flex-1 bg-transparent text-[11px] focus:outline-none"
            style={{ color: "#dff3fd" }}
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {notes.length === 0 ? (
          <p
            className="text-center py-8 text-[10px] tracking-[0.1em]"
            style={{ color: "rgba(0,180,216,0.25)" }}
          >
            {searchQuery ? "Không tìm thấy ghi chú" : "Chưa có ghi chú"}
          </p>
        ) : (
          <>
            {pinned.length > 0 && (
              <>
                <p
                  className="px-2 pb-1 text-[9px] font-semibold tracking-[0.15em]"
                  style={{ color: "rgba(0,180,216,0.4)" }}
                >
                  GHIM
                </p>
                <div className="space-y-0.5 mb-3">
                  {pinned.map((note) => (
                    <NoteItem
                      key={note.id}
                      note={note}
                      selected={selectedId === note.id}
                      timezone={timezone}
                      onSelect={() => onSelect(note.id)}
                      onPin={() => onPin(note.id, note.pinned)}
                      onDelete={() => onDelete(note.id)}
                    />
                  ))}
                </div>
              </>
            )}

            {unpinned.length > 0 && (
              <>
                {pinned.length > 0 && (
                  <p
                    className="px-2 pb-1 text-[9px] font-semibold tracking-[0.15em]"
                    style={{ color: "rgba(0,180,216,0.4)" }}
                  >
                    TẤT CẢ
                  </p>
                )}
                <div className="space-y-0.5">
                  {unpinned.map((note) => (
                    <NoteItem
                      key={note.id}
                      note={note}
                      selected={selectedId === note.id}
                      timezone={timezone}
                      onSelect={() => onSelect(note.id)}
                      onPin={() => onPin(note.id, note.pinned)}
                      onDelete={() => onDelete(note.id)}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
