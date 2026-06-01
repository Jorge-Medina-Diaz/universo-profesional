import { useState } from "react";
import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { ConfirmCard } from "../cards/ConfirmCard";
import { DocumentPreviewCard } from "../cards/DocumentPreviewCard";
import { documents } from "@/shared/api";
import { toast } from "@/ui";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

type DocBody = Parameters<typeof documents.generate>[0];

/**
 * Agentic document generation card. The agent already has every parameter in
 * its tool args, so it GENERATES the document inline on confirm (no bouncing
 * the user to an empty /cv/new form to press a button — the old anti-pattern)
 * and then opens the result in the viewer, which now carries the global agent
 * dock so the conversation continues there. Failures are surfaced loudly
 * (toast) — never silent (see [[no-silent-errors]]).
 */
function InlineGenerate({
  respond,
  target,
  description,
  payload,
  body,
}: {
  respond?: (s: string) => void;
  target: string;
  description?: string;
  payload?: Record<string, unknown>;
  body: DocBody;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <ConfirmCard
      actionLabel="Generar"
      target={target}
      description={description}
      payload={payload}
      pending={busy}
      confirmLabel="Generar ahora"
      onConfirm={async () => {
        if (busy) return;
        setBusy(true);
        try {
          const resp = await documents.generate(body);
          if (resp.render_status === "failed") {
            toast.error(
              "El documento se generó con errores de render",
              "Ábrelo para revisarlo o pídeme que lo reintente.",
            );
          }
          respond?.(
            JSON.stringify({
              ok: true,
              document_id: resp.document_id,
              render_status: resp.render_status,
            }),
          );
          // Show the real result (the viewer carries the agent dock).
          window.location.hash = `#/documents/${resp.document_id}`;
        } catch (e) {
          toast.error("No se pudo generar el documento", (e as Error)?.message);
          setBusy(false); // let the user retry the same card
        }
      }}
      onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
    />
  );
}

export function useDocumentActions(
  _saving: SavingState,
  _setSaving: (s: SavingState) => void,
  _setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  _qc: ReturnType<typeof useQueryClient>,
) {
  useCopilotAction({
    name: "propose_cover_letter",
    description:
      "Offer to generate a cover letter for a job description. Pass job_description and optional job_url + company + title.",
    parameters: [
      { name: "job_description", type: "string", required: true },
      { name: "job_url", type: "string" },
      { name: "company", type: "string" },
      { name: "title", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <InlineGenerate
        respond={respond}
        target="Carta de presentación"
        description="La genero ahora con tu universo y esta oferta, y te la abro."
        payload={{
          puesto: args.title,
          empresa: args.company,
          fuente: args.job_url,
        }}
        body={{
          kind: "cover_letter",
          job_description: args.job_description as string | undefined,
          job_url: args.job_url as string | undefined,
        }}
      />
    ),
  });

  useCopilotAction({
    name: "propose_document_generation",
    description:
      "Offer to generate a NEW document (CV or cover letter) after conversational discovery. Pass kind, template, tone, language, and optional job details.",
    parameters: [
      { name: "kind", type: "string", required: true },
      { name: "template", type: "string", required: true },
      { name: "tone", type: "string", required: true },
      { name: "language", type: "string" },
      { name: "job_description", type: "string" },
      { name: "job_url", type: "string" },
      { name: "job_title", type: "string" },
      { name: "company", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <InlineGenerate
        respond={respond}
        target={args.kind === "cover_letter" ? "Carta de presentación" : "CV"}
        description={`Plantilla: ${String(args.template)} · Tono: ${String(args.tone)} · Idioma: ${String(args.language ?? "es")}`}
        payload={{
          oferta: args.job_title,
          empresa: args.company,
          plantilla: args.template,
          tono: args.tone,
        }}
        body={{
          kind: (args.kind as "cv" | "cover_letter") ?? "cv",
          template: args.template as string | undefined,
          tone: args.tone as string | undefined,
          language: (args.language as string | undefined) ?? "es",
          job_description: args.job_description as string | undefined,
          job_url: args.job_url as string | undefined,
        }}
      />
    ),
  });

  useCopilotAction({
    name: "propose_cv_regenerate",
    description:
      "Propose regenerating an existing document with new template/language/tone (produces a fresh version).",
    parameters: [
      { name: "document_id", type: "string", required: true },
      { name: "template_override", type: "string" },
      { name: "language_override", type: "string" },
      { name: "tone_override", type: "string" },
      { name: "rationale", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <InlineGenerate
        respond={respond}
        target="Regenerar documento"
        description={(args.rationale as string) ?? undefined}
        payload={{
          plantilla: args.template_override,
          idioma: args.language_override,
          tono: args.tone_override,
        }}
        body={{
          kind: "cv",
          template: args.template_override as string | undefined,
          language: args.language_override as string | undefined,
          tone: args.tone_override as string | undefined,
        }}
      />
    ),
  });

  useCopilotAction({
    name: "present_document_preview",
    description:
      "Render an inline preview of a generated document with collapsible sections.",
    available: "frontend",
    parameters: [
      { name: "document_id", type: "string", required: true },
      { name: "offer_regenerate", type: "boolean" },
      { name: "offer_variant", type: "boolean" },
    ] satisfies CopilotActionParams,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <DocumentPreviewCard
        documentId={args.document_id as string}
        onRegenerate={
          args.offer_regenerate
            ? () => {
                // Explicit "open the full editor" affordance (power users).
                window.location.hash = "#/cv/new";
              }
            : undefined
        }
        onGenerateVariant={
          args.offer_variant
            ? () => {
                window.location.hash = "#/cv/new";
              }
            : undefined
        }
      />
    ),
  });
}
