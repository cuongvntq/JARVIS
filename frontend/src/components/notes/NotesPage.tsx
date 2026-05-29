"use client";

import { useEffect, useState } from "react";
import { Plus, FileText, Loader2 } from "lucide-react";
import { useNotes, useCreateNote, useUpdateNote, usePinNote, useDeleteNote } from "@/hooks/useNotes";
import { useAuthStore } from "@/stores/authStore";
import NoteList from "./NoteList";
import NoteEditor from "./NoteEditor";
import type { NoteOut } from "@/lib/types/api";

export default function NotesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Keeps the last known note data so the editor doesn't reset when the
  // search query filters the selected note out of the visible list.
  const [selectedNoteData, setSelectedNoteData] = useState<NoteOut | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const user = useAuthStore((s) => s.user);
  const timezone = user?.timezone ?? "UTC";

  const { data, isLoading, isError } = useNotes(searchQuery || undefined);
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const pinNote = usePinNote();
  const deleteNote = useDeleteNote();

  const notes: NoteOut[] = data?.items ?? [];

  // Update selectedNoteData when the note appears in the current list (e.g. after
  // a save/invalidation) but do NOT clear it just because the search hides it.
  useEffect(() => {
    if (!selectedId) return;
    const found = notes.find((n) => n.id === selectedId);
    if (found) setSelectedNoteData(found);
  }, [notes, selectedId]);

  const editorNote = isCreating ? null : selectedNoteData;
  const showEditor = isCreating || selectedId !== null;

  function handleSelectNote(id: string) {
    const note = notes.find((n) => n.id === id) ?? null;
    setSelectedId(id);
    setSelectedNoteData(note);
    setIsCreating(false);
  }

  function handleNewNote() {
    setSelectedId(null);
    setSelectedNoteData(null);
    setIsCreating(true);
  }

  function handleCloseEditor() {
    setSelectedId(null);
    setSelectedNoteData(null);
    setIsCreating(false);
  }

  async function handleSave(data: { title: string; content: string; tags: string[] }) {
    if (isCreating) {
      const created = await createNote.mutateAsync({
        title: data.title,
        content: data.content,
        tags: data.tags,
        source: "ui",
      });
      setIsCreating(false);
      setSelectedId(created.id);
      setSelectedNoteData(created);
    } else if (selectedId) {
      const updated = await updateNote.mutateAsync({
        id: selectedId,
        data: { title: data.title, content: data.content, tags: data.tags },
      });
      setSelectedNoteData(updated);
    }
  }

  function handlePin(id: string, pinned: boolean) {
    pinNote.mutate({ id, pinned });
  }

  function handleDelete(id: string) {
    deleteNote.mutate(id);
    if (selectedId === id) {
      setSelectedId(null);
      setSelectedNoteData(null);
    }
  }

  const isSaving = createNote.isPending || updateNote.isPending;

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "#0b1929" }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "rgba(0,180,216,0.12)" }}
      >
        <div className="flex items-center gap-3">
          <FileText size={16} style={{ color: "#00b4d8" }} />
          <h1
            className="text-sm font-bold tracking-[0.25em]"
            style={{ fontFamily: "var(--font-orbitron)", color: "#00b4d8" }}
          >
            NOTES
          </h1>
          {notes.length > 0 && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded-full"
              style={{ backgroundColor: "rgba(0,180,216,0.15)", color: "#5e8a9e" }}
            >
              {notes.length}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleNewNote}
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

      {/* Body: list + editor */}
      <div className="flex flex-1 min-h-0">
        {/* Left: note list */}
        <div
          className="flex flex-col border-r"
          style={{
            width: showEditor ? "260px" : "100%",
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
            <NoteList
              notes={notes}
              selectedId={showEditor && !isCreating ? selectedId : null}
              timezone={timezone}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onSelect={handleSelectNote}
              onPin={handlePin}
              onDelete={handleDelete}
            />
          )}
        </div>

        {/* Right: editor */}
        {showEditor && (
          <div className="flex-1 min-w-0">
            <NoteEditor
              note={editorNote}
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
