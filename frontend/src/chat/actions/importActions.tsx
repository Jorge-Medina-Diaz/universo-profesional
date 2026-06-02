import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "@/ui";
import { integrations } from "@/shared/api-extra";
import { queryKeys } from "@/shared/queryKeys";
import { EntryCard } from "../cards/EntryCard";
import { ImportReviewCard, type ImportGroup } from "../cards/ImportReviewCard";
import { PdfImportCard } from "../cards/PdfImportCard";
import { normalizeImportItem, coherenceUpsert } from "./shared";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

export function useImportActions(
  saving: SavingState,
  setSaving: (s: SavingState) => void,
  setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  qc: ReturnType<typeof useQueryClient>,
) {
  useCopilotAction({
    name: "propose_github_sync",
    description: "Propose pulling the user's GitHub profile. User confirms.",
    parameters: [] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({ respond }) => (
      <EntryCard
        title="Importar perfil de GitHub"
        details={{
          contenido: "repos · lenguajes · pinned · contributions · orgs",
          duracion: "~10-20 s",
        }}
        pending={saving === "gh-sync"}
        ctaLabel="Sincronizar ahora"
        onConfirm={async () => {
          setSaving("gh-sync");
          try {
            const r = await integrations.github.sync();
            qc.invalidateQueries({ queryKey: queryKeys.universe.all });
            respond?.(`Sync ok — ${JSON.stringify(r)}`);
          } catch (e) {
            respond?.(`Sync error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onReject={() => respond?.("Cancelled.")}
      />
    ),
  });

  useCopilotAction({
    name: "propose_brightdata_sync",
    description: "Propose a Bright Data LinkedIn sync (PRO tier).",
    parameters: [] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({ respond }) => (
      <EntryCard
        title="Sincronizar LinkedIn (Bright Data, PRO)"
        details={{
          contenido: "datos públicos del perfil",
          requiere: "plan PRO + URL pública",
        }}
        pending={saving === "brightdata"}
        ctaLabel="Ir a Conexiones"
        onConfirm={async () => {
          setSaving("brightdata");
          window.location.hash = "#/connections";
          respond?.("Redirected to /connections.");
          setSaving(null);
        }}
        onReject={() => respond?.("Cancelled.")}
      />
    ),
  });

  useCopilotAction({
    name: "propose_pdf_import",
    description:
      "Open an inline CV-PDF importer in the chat: the user drops their PDF, " +
      "reviews the parsed entries (confidence-flagged, least-certain first) and " +
      "imports them — all without leaving the conversation. Use whenever the user " +
      "wants to import/upload a CV or résumé PDF.",
    parameters: [] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({ respond }: { respond?: (s: string) => void }) => (
      <PdfImportCard
        onDone={(summary) => respond?.(JSON.stringify(summary))}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
        onCommitted={() => {
          qc.invalidateQueries({ queryKey: queryKeys.universe.all });
          qc.invalidateQueries({ queryKey: queryKeys.graph.snapshot });
          qc.invalidateQueries({ queryKey: queryKeys.coherence.changes });
        }}
      />
    ),
  });

  // --- Batch import review (trusted ingestion: CV / LinkedIn / dictated) ----
  const commitImport = async (
    selected: ImportGroup[],
  ): Promise<{ committed: Record<string, number>; total: number }> => {
    setSaving("import-review");
    try {
      const committed: Record<string, number> = {};
      const failed: { kind: string; error: string }[] = [];
      let total = 0;
      let lastResp: UpsertResponse | null = null;
      for (const g of selected) {
        for (const item of g.items) {
          try {
            const clean = normalizeImportItem(g.kind, item as Record<string, unknown>);
            const payload = g.kind === "skill" ? { category: "hard", ...clean } : clean;
            const resp = await coherenceUpsert(g.kind, payload);
            lastResp = resp;
            // A malformed CREATE returns 200 {status:"noop", entity_id:null} — a
            // SILENT drop unless we treat it as a failure (no-silent-errors rule).
            // created/merged/suggested are genuine outcomes; noop/null is not.
            const notSaved =
              resp.status === "noop" || (resp.entity_id == null && resp.suggestion_id == null);
            if (notSaved) {
              failed.push({ kind: g.kind, error: resp.reason || "no se guardó (dato inválido o duplicado)" });
            } else {
              committed[g.kind] = (committed[g.kind] ?? 0) + 1;
              total += 1;
            }
          } catch (e) {
            failed.push({ kind: g.kind, error: (e as Error).message });
          }
        }
      }
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      qc.invalidateQueries({ queryKey: queryKeys.coherence.changes });
      if (lastResp) setLastOutcome({ kind: "import", resp: lastResp });
      if (failed.length) {
        const detail = failed
          .slice(0, 3)
          .map((f) => `${f.kind}: ${f.error}`)
          .join(" · ");
        toast.error(
          `No se pudieron importar ${failed.length} elemento(s)`,
          failed.length > 3 ? `${detail} …` : detail,
        );
      }
      return { committed, total };
    } finally {
      setSaving(null);
    }
  };

  useCopilotAction({
    name: "present_import_review",
    description:
      "Show a single batch-review card for an imported/dictated set of entities. The user reviews the whole set, deselects parts, and commits them together.",
    parameters: [
      { name: "groups", type: "object[]", required: true },
      { name: "title", type: "string" },
      { name: "source", type: "string" },
      { name: "intro", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ImportReviewCard
        title={args.title as string | undefined}
        intro={args.intro as string | undefined}
        source={args.source as string | undefined}
        groups={(args.groups as ImportGroup[]) ?? []}
        pending={saving === "import-review"}
        onConfirm={async (selected) => {
          const res = await commitImport(selected);
          respond?.(JSON.stringify(res));
          return res;
        }}
        onCancel={() =>
          respond?.(JSON.stringify({ committed: {}, total: 0, cancelled: true }))
        }
      />
    ),
  });
}
