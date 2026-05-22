import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Share2, FileDown, Sparkles, ArrowLeftRight } from "lucide-react";

import { documents } from "@/shared/api";
import { useChatState } from "@/chat/state";
import {
  Badge,
  Button,
  Card,
  cn,
  PageHeader,
  PaperPlaneIllustration,
  Reveal,
  Stagger,
  Surface,
  toast,
} from "@/ui";

interface Doc {
  id: string;
  kind: string;
  template: string;
  language: string;
  created_at: string;
  has_pdf: boolean;
  has_docx: boolean;
  share_token?: string | null;
}

export function DocumentsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["documents"], queryFn: () => documents.list() });

  // Chat focus → scroll-to + highlight if the agent is talking about a doc.
  const chatFocus = useChatState();
  const focusedDocId = chatFocus.entity === "document" ? chatFocus.id : null;
  useEffect(() => {
    if (!focusedDocId) return;
    const t = setTimeout(() => {
      const el = document.querySelector(`[data-document-id="${focusedDocId}"]`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
    return () => clearTimeout(t);
  }, [focusedDocId]);

  const share = useMutation({
    mutationFn: (id: string) => documents.share(id),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      const url = `${window.location.origin}/#/share/${res?.share_token ?? ""}`;
      void navigator.clipboard?.writeText(url).catch(() => {});
      toast.success("Enlace copiado", "Listo para compartir");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos generar el enlace", (e as Error).message),
  });

  return (
    <Surface width="lg" spacing="md">
      <PageHeader
        eyebrow="Histórico"
        title="Documentos"
        subtitle="Cada CV o carta generada queda guardada y compartible."
        actions={
          <>
            {(list.data?.length ?? 0) >= 2 && (
              <Button
                variant="outline"
                onClick={() => (window.location.hash = "#/compare")}
                leadingIcon={<ArrowLeftRight size={14} />}
              >
                Comparar
              </Button>
            )}
            <Button
              onClick={() => (window.location.hash = "#/cv/new")}
              leadingIcon={<Sparkles size={14} />}
            >
              {t("cv.generate")}
            </Button>
          </>
        }
      />

      {list.isLoading && (
        <Reveal>
          <Card padding="md">
            <p className="text-sm text-stone">{t("common.loading")}</p>
          </Card>
        </Reveal>
      )}

      {list.data?.length === 0 && (
        <Reveal>
          <Card padding="lg" className="text-center space-y-4">
            <PaperPlaneIllustration className="mx-auto" />
            <h3 className="text-heading-sm font-medium tracking-tight">
              Aún no has generado documentos
            </h3>
            <p className="text-sm text-stone max-w-md mx-auto">
              Pega una oferta de trabajo y el agente genera un CV adaptado en segundos.
            </p>
            <div className="pt-2">
              <Button onClick={() => (window.location.hash = "#/cv/new")}>
                Generar mi primer CV
              </Button>
            </div>
          </Card>
        </Reveal>
      )}

      {list.data && list.data.length > 0 && (
        <Stagger className="flex flex-col gap-3 md:gap-4" delayStep={0.04}>
          {list.data.map((d: Doc) => (
            <DocCard
              key={d.id}
              doc={d}
              focused={focusedDocId === d.id}
              onShare={() => share.mutate(d.id)}
            />
          ))}
        </Stagger>
      )}
    </Surface>
  );
}

function DocCard({
  doc,
  focused,
  onShare,
}: {
  doc: Doc;
  focused: boolean;
  onShare: () => void;
}) {
  return (
    <Card
      padding="lg"
      data-document-id={doc.id}
      className={cn(
        focused && "ring-2 ring-sunbeam ring-offset-2 ring-offset-canvas shadow-soft",
      )}
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <a
          href={`#/documents/${doc.id}`}
          className="flex items-start gap-3 min-w-0 flex-1 group"
        >
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-canvas text-ink shrink-0"
          >
            <FileText size={18} />
          </span>
          <div className="min-w-0 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-medium text-ink group-hover:underline underline-offset-4">
                {doc.kind.toUpperCase()}
              </h3>
              <Badge tone="stone" size="sm">
                {doc.template}
              </Badge>
              <Badge tone="stone" size="sm">
                {doc.language}
              </Badge>
            </div>
            <p className="text-xs text-stone">
              {new Date(doc.created_at).toLocaleString()}
            </p>
            {doc.share_token && (
              <p className="text-xs text-stone">
                Compartido en{" "}
                <code className="bg-canvas px-1.5 py-0.5 rounded">
                  /share/{doc.share_token}
                </code>
              </p>
            )}
          </div>
        </a>
        <div className="flex gap-2 flex-wrap">
          {doc.has_pdf && (
            <DownloadButton href={`/api/v1/documents/${doc.id}/pdf`} label="PDF" />
          )}
          {doc.has_docx && (
            <DownloadButton href={`/api/v1/documents/${doc.id}/docx`} label="DOCX" />
          )}
          <DownloadButton href={`/api/v1/documents/${doc.id}/json`} label="JSON" />
          <Button
            size="sm"
            variant="ghost"
            onClick={onShare}
            leadingIcon={<Share2 size={14} />}
          >
            Compartir
          </Button>
        </div>
      </div>
    </Card>
  );
}

function DownloadButton({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1.5 h-9 px-3 rounded-btn bg-canvas hover:bg-black/[0.04] text-ink text-xs font-medium transition-colors duration-180 ease-pirsch"
    >
      <FileDown size={12} />
      {label}
    </a>
  );
}
