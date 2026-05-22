/**
 * Drag-and-drop file upload primitive. Click to pick, or drag a file in.
 *
 * Single-file by default; pass `multiple` for multi-file scenarios. Filters
 * by extension if `accept` provided (extension-only, no MIME magic). Visual
 * state: idle / hover / dropping. Disabled state respected.
 */
import { useCallback, useRef, useState, type DragEvent, type ReactNode } from "react";
import { Upload, Loader2 } from "lucide-react";
import { cn } from "./cn";

export interface DropZoneProps {
  accept?: string; // e.g. ".pdf,.zip,application/pdf"
  multiple?: boolean;
  disabled?: boolean;
  loading?: boolean;
  /** Bytes; if exceeded, onError is called with a message instead of onFiles. */
  maxBytes?: number;
  onFiles: (files: File[]) => void;
  onError?: (message: string) => void;
  label?: ReactNode;
  hint?: ReactNode;
  /** Compact = button-like; default = card-like dashed surface. */
  variant?: "card" | "compact";
  className?: string;
}

export function DropZone({
  accept,
  multiple = false,
  disabled,
  loading,
  maxBytes,
  onFiles,
  onError,
  label,
  hint,
  variant = "card",
  className,
}: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const dragCountRef = useRef(0);

  const handle = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const list = multiple ? Array.from(files) : [files[0]];
      if (maxBytes != null) {
        const tooBig = list.find((f) => f.size > maxBytes);
        if (tooBig) {
          onError?.(
            `"${tooBig.name}" supera ${(maxBytes / (1024 * 1024)).toFixed(0)} MB.`,
          );
          return;
        }
      }
      onFiles(list);
    },
    [multiple, maxBytes, onFiles, onError],
  );

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current = 0;
    setOver(false);
    if (disabled || loading) return;
    handle(e.dataTransfer?.files ?? null);
  };

  const onDragOver = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onDragEnter = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled || loading) return;
    dragCountRef.current++;
    setOver(true);
  };

  const onDragLeave = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current = Math.max(0, dragCountRef.current - 1);
    if (dragCountRef.current === 0) setOver(false);
  };

  if (variant === "compact") {
    return (
      <label
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        className={cn(
          "inline-flex items-center gap-2 rounded-btn px-4 py-2.5 text-sm font-medium cursor-pointer transition-all duration-180 ease-pirsch",
          over && !disabled
            ? "bg-leaf text-ink"
            : "bg-sunbeam text-ink hover:bg-[#ffcf45]",
          (disabled || loading) && "opacity-60 cursor-not-allowed",
          className,
        )}
      >
        {loading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
        <span>{label ?? "Subir archivo"}</span>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled || loading}
          onChange={(e) => handle(e.target.files)}
          className="sr-only"
        />
      </label>
    );
  }

  return (
    <label
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed px-6 py-8 cursor-pointer transition-all duration-180 ease-pirsch text-center",
        over && !disabled
          ? "border-leaf bg-leaf-soft/40"
          : "border-ink/15 bg-canvas hover:border-ink/30",
        (disabled || loading) && "opacity-60 cursor-not-allowed",
        className,
      )}
    >
      <span
        aria-hidden
        className={cn(
          "inline-flex items-center justify-center w-10 h-10 rounded-full transition-colors",
          over ? "bg-leaf text-ink" : "bg-surface text-stone",
        )}
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
      </span>
      <div className="space-y-0.5">
        <div className="text-sm font-medium text-ink">
          {label ?? (over ? "Suelta aquí" : "Arrastra un archivo o haz clic")}
        </div>
        {hint && <div className="text-xs text-stone">{hint}</div>}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled || loading}
        onChange={(e) => handle(e.target.files)}
        className="sr-only"
      />
    </label>
  );
}
