/**
 * Inline upload dropzone inside the chat. Lets the user drop a PDF / image
 * without leaving the conversation. The blob is POSTed to the appropriate
 * endpoint depending on `purpose`.
 *
 * Returns to the agent: { uploaded: bool, file_url?: string, kind: 'pdf'|'image'|'other', name?: string }
 */
import { useState } from "react";
import { Check, FileUp, X } from "lucide-react";
import { useAuthStore } from "@/shared/api";
import { Badge, Button, ChatMessageMotion, DropZone, cn, toast } from "@/ui";

export interface UploadInlineCardProps {
  purpose: string;
  accept?: string;
  maxBytes?: number;
  onComplete: (payload: {
    uploaded: boolean;
    file_url?: string;
    kind: "pdf" | "image" | "other";
    name?: string;
  }) => void;
  onCancel: () => void;
}

/** Map a MIME prefix to the upload endpoint we actually have wired up.
 *  PDF goes through the parse endpoint (returns parsed session for the
 *  agent to inspect); image goes to the avatar endpoint. */
function pickEndpoint(file: File): { url: string; kind: "pdf" | "image" | "other" } {
  if (file.type === "application/pdf") {
    return { url: "/api/v1/integrations/pdf/parse", kind: "pdf" };
  }
  if (file.type.startsWith("image/")) {
    return { url: "/api/v1/users/me/photo", kind: "image" };
  }
  return { url: "", kind: "other" };
}

export function UploadInlineCard({
  purpose,
  accept = "application/pdf",
  maxBytes = 10 * 1024 * 1024,
  onComplete,
  onCancel,
}: UploadInlineCardProps) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  const handle = async (files: File[]) => {
    const f = files[0];
    if (!f) return;
    const { url, kind } = pickEndpoint(f);
    if (!url) {
      toast.error("Tipo de archivo no soportado");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const token = useAuthStore.getState().accessToken ?? "";
      const resp = await fetch(url, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const data = (await resp.json().catch(() => ({}))) as { file_url?: string };
      setDone(f.name);
      onComplete({
        uploaded: true,
        kind,
        name: f.name,
        file_url: data.file_url,
      });
      toast.success("Subida completada", f.name);
    } catch (e) {
      onComplete({ uploaded: false, kind });
      toast.error("Subida fallida", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-5 my-3 max-w-md border border-ink/[0.06] shadow-soft">
        <header className="flex items-start gap-3 mb-3">
          <span
            aria-hidden
            className={cn(
              "inline-flex items-center justify-center w-9 h-9 rounded-full shrink-0",
              done ? "bg-leaf-soft text-leaf-ink" : "bg-sunbeam-soft text-sunbeam-ink",
            )}
          >
            {done ? <Check size={14} /> : <FileUp size={14} />}
          </span>
          <div className="min-w-0 space-y-1">
            <h4 className="font-medium text-sm text-ink leading-tight">{purpose}</h4>
            {done && (
              <Badge tone="leaf" size="sm">
                {done}
              </Badge>
            )}
          </div>
        </header>
        {!done && (
          <DropZone
            accept={accept}
            maxBytes={maxBytes}
            loading={busy}
            onFiles={handle}
            onError={(msg) => toast.error("Archivo rechazado", msg)}
            label={busy ? "Subiendo…" : "Arrastra o haz clic"}
            hint={`Hasta ${Math.round(maxBytes / (1024 * 1024))} MB`}
          />
        )}
        <div className="flex justify-end mt-3">
          <Button
            size="sm"
            variant="ghost"
            onClick={onCancel}
            leadingIcon={<X size={14} />}
          >
            {done ? "Cerrar" : "Cancelar"}
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}
