import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { ConfirmCard } from "../cards/ConfirmCard";
import { EntryCard } from "../cards/EntryCard";
import { DocumentPreviewCard } from "../cards/DocumentPreviewCard";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

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
      <EntryCard
        title="Generar carta de presentación"
        kind="cover_letter"
        details={{
          puesto: args.title as string | undefined,
          empresa: args.company as string | undefined,
          fuente: args.job_url as string | undefined,
        }}
        pending={false}
        ctaLabel="Abrir generador"
        ctaDescription="Te llevamos al generador con la oferta y el modo carta pre-seleccionados."
        onConfirm={() => {
          try {
            sessionStorage.setItem(
              "cvs-saas-prefill-job",
              JSON.stringify({
                job_url: args.job_url as string | undefined,
                job_description: args.job_description as string,
                title: args.title as string | undefined,
                company_name: args.company as string | undefined,
              }),
            );
            sessionStorage.setItem("cvs-saas-prefill-kind", "cover_letter");
          } catch {
            /* ignore */
          }
          window.location.hash = "#/cv/new";
          respond?.("opened-generator");
        }}
        onReject={() => respond?.("cancelled")}
      />
    ),
  });

  useCopilotAction({
    name: "propose_cv_regenerate",
    description:
      "Propose regenerating an existing document with new template/language/tone.",
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
      <ConfirmCard
        actionLabel="Regenerar"
        target="Documento"
        description={(args.rationale as string) ?? undefined}
        payload={{
          plantilla: args.template_override,
          idioma: args.language_override,
          tono: args.tone_override,
        }}
        confirmLabel="Abrir generador"
        onConfirm={() => {
          try {
            sessionStorage.setItem(
              "cvs-saas-cv-regenerate",
              JSON.stringify({
                document_id: args.document_id,
                template: args.template_override,
                language: args.language_override,
                tone: args.tone_override,
              }),
            );
          } catch {
            /* ignore */
          }
          window.location.hash = "#/cv/new";
          respond?.(JSON.stringify({ ok: true, redirected: true }));
        }}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
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
    ] satisfies CopilotActionParams,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <DocumentPreviewCard
        documentId={args.document_id as string}
        onRegenerate={
          args.offer_regenerate
            ? () => {
                window.location.hash = "#/cv/new";
              }
            : undefined
        }
      />
    ),
  });
}
