/**
 * DocumentPreviewWidget — minimal widget wrap around a generated document.
 *
 * Data: { document_id, title?, kind?, template?, share_url? }
 * Real preview rendering lives in DocumentPreviewCard (HITL); this widget is
 * for the display-only "browse later" case.
 */
import { FileText, ExternalLink } from "lucide-react";

interface DocPreviewData {
  document_id?: string;
  title?: string;
  kind?: string;
  template?: string;
  share_url?: string;
}

export function DocumentPreviewWidget({ data }: { data: DocPreviewData }) {
  if (!data.document_id) {
    return <p className="text-sm text-stone">Sin documento referenciado.</p>;
  }
  return (
    <div className="rounded-card bg-surface border border-hairline px-3 py-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-leaf-soft text-leaf-ink"
        >
          <FileText size={12} />
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-ink truncate">
            {data.title ?? "Documento"}
          </div>
          <div className="text-[11px] text-stone">
            {data.kind ?? "—"} · {data.template ?? "—"}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <a
          href={`#/documents/${data.document_id}`}
          className="text-ink underline-offset-2 hover:underline"
        >
          abrir →
        </a>
        {data.share_url ? (
          <a
            href={data.share_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-stone hover:text-ink"
          >
            compartir <ExternalLink size={10} />
          </a>
        ) : null}
      </div>
    </div>
  );
}
