/**
 * InlineEntityEditor — double-click any paragraph in an agent reply to edit
 * it in-place. When saved, the correction is either sent back to the agent
 * as a follow-up message or, if the entity is recognised, patched directly
 * via the universe API.
 *
 * This keeps the user inside the chat flow — no proposal cards, no modals.
 */
import { useState, useRef, useCallback, useEffect } from "react";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { Check, X, Pencil } from "lucide-react";


interface InlineEditState {
  original: string;
  draft: string;
  top: number;
  left: number;
}

interface Props {
  children: React.ReactNode;
  onEdit: (original: string, corrected: string) => void;
}

export function InlineEntityEditor({ children, onEdit }: Props) {
  const [edit, setEdit] = useState<InlineEditState | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    // Only allow editing on textual elements inside the prose block.
    const paragraph = target.closest("p, li, td, blockquote, h1, h2, h3, h4");
    if (!paragraph) return;
    const text = paragraph.textContent ?? "";
    if (!text.trim() || text.length < 3) return;

    const rect = paragraph.getBoundingClientRect();
    const wrapperRect = wrapperRef.current?.getBoundingClientRect();
    // Clamp within the wrapper so the popover never spills off-screen.
    const wrapperWidth = wrapperRect?.width ?? 0;
    const popWidth = Math.min(520, wrapperWidth || 520);
    const rawLeft = rect.left - (wrapperRect?.left ?? 0);
    const rawTop = rect.top - (wrapperRect?.top ?? 0);
    setEdit({
      original: text,
      draft: text,
      top: Math.max(0, rawTop),
      left: Math.max(0, Math.min(rawLeft, Math.max(0, wrapperWidth - popWidth))),
    });
  }, []);

  useEffect(() => {
    if (edit) {
      const el = textareaRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(el.value.length, el.value.length);
      }
    }
  }, [edit]);

  const save = useCallback(() => {
    if (!edit) return;
    if (edit.draft.trim() && edit.draft !== edit.original) {
      onEdit(edit.original, edit.draft);
    }
    setEdit(null);
  }, [edit, onEdit]);

  const cancel = useCallback(() => setEdit(null), []);

  useEscapeKey(cancel, !!edit);

  useEffect(() => {
    if (!edit) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) save();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [edit, save]);

  // Focus trap: keep Tab cycling within the editor popover while it is open, so
  // keyboard users can't tab out of the modal editor into the page behind it.
  useEffect(() => {
    const node = popoverRef.current;
    if (!edit || !node) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusables = node.querySelectorAll<HTMLElement>(
        'textarea, button, [href], [tabindex]:not([tabindex="-1"])',
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    node.addEventListener("keydown", handler);
    return () => node.removeEventListener("keydown", handler);
  }, [edit]);

  return (
    <div ref={wrapperRef} className="inline-editor-wrapper" onDoubleClick={handleDoubleClick}>
      {children}
      {edit && (
        <div
          ref={popoverRef}
          role="dialog"
          aria-modal="true"
          aria-label="Editar en el chat"
          className="inline-editor-popover"
          style={{ top: edit.top, left: edit.left, width: "100%", maxWidth: 520 }}
        >
          <div className="inline-editor-popover__head">
            <Pencil size={11} strokeWidth={2.5} />
            <span className="inline-editor-popover__title">Editar en el chat</span>
          </div>
          <textarea
            ref={textareaRef}
            value={edit.draft}
            onChange={(e) => setEdit((prev) => (prev ? { ...prev, draft: e.target.value } : prev))}
            rows={3}
            className="inline-editor-popover__input"
          />
          <div className="inline-editor-popover__actions">
            <button type="button" onClick={save} className="inline-editor-popover__btn inline-editor-popover__btn--primary">
              <Check size={12} />
              Guardar
            </button>
            <button type="button" onClick={cancel} className="inline-editor-popover__btn">
              <X size={12} />
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
