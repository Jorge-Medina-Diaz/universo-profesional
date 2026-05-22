/**
 * Generic preview table for import flows (LinkedIn DMA/Bright Data/ZIP, PDF CV).
 *
 * Backend returns a `parsed` blob with per-section arrays (experiences,
 * educations, skills, ...). User picks which rows to commit. Sections come
 * pre-grouped; each row has a checkbox and short summary. Bulk select per
 * section, plus search across all rows.
 */
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, Search, Check } from "lucide-react";
import { Badge, Button, Card, cn, ProgressSteps, type ProgressStep } from "@/ui";

export interface ImportPreviewSection {
  /** Key in the parsed blob and selection map (`experiences`, `skills`, ...). */
  key: string;
  /** UI label. */
  label: string;
  /** Rows in this section. */
  rows: Array<Record<string, unknown> & { id?: string | number }>;
  /** Row → display summary string. */
  summarize: (row: Record<string, unknown>) => string;
  /** Row → optional sub-line (e.g. dates). */
  sublabel?: (row: Record<string, unknown>) => string | undefined;
}

export interface ImportPreviewSelection {
  [sectionKey: string]: number[]; // row indices to commit
}

export interface ImportPreviewTableProps {
  sections: ImportPreviewSection[];
  pending?: boolean;
  /** When committing, show the in-flight pipeline. */
  commitSteps?: ProgressStep[];
  onCommit: (selection: ImportPreviewSelection) => void | Promise<void>;
  onCancel?: () => void;
  commitLabel?: string;
  source?: "linkedin-dma" | "linkedin-brightdata" | "linkedin-zip" | "pdf" | "github";
}

export function ImportPreviewTable({
  sections,
  pending = false,
  commitSteps,
  onCommit,
  onCancel,
  commitLabel = "Importar selección",
  source,
}: ImportPreviewTableProps) {
  const [query, setQuery] = useState("");
  const [openSections, setOpenSections] = useState<Set<string>>(
    () => new Set(sections.filter((s) => s.rows.length).map((s) => s.key)),
  );
  const [selection, setSelection] = useState<ImportPreviewSelection>(() =>
    Object.fromEntries(
      sections.map((s) => [s.key, s.rows.map((_, i) => i)]), // start all selected
    ),
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sections;
    return sections
      .map((s) => {
        const filteredRows = s.rows
          .map((row, i) => ({ row, i }))
          .filter(({ row }) => s.summarize(row).toLowerCase().includes(q));
        return { ...s, _filteredRows: filteredRows };
      })
      .filter((s) => (s._filteredRows ?? []).length > 0);
  }, [sections, query]);

  const totalSelected = useMemo(
    () =>
      Object.values(selection).reduce((acc, indices) => acc + indices.length, 0),
    [selection],
  );
  const totalRows = useMemo(
    () => sections.reduce((acc, s) => acc + s.rows.length, 0),
    [sections],
  );

  const toggleSection = (key: string) =>
    setOpenSections((set) => {
      const next = new Set(set);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const toggleRow = (key: string, idx: number) =>
    setSelection((sel) => {
      const current = sel[key] ?? [];
      const exists = current.includes(idx);
      return {
        ...sel,
        [key]: exists ? current.filter((j) => j !== idx) : [...current, idx],
      };
    });

  const toggleAllSection = (key: string, allIndices: number[]) =>
    setSelection((sel) => {
      const current = sel[key] ?? [];
      const allSelected = allIndices.every((i) => current.includes(i));
      return {
        ...sel,
        [key]: allSelected
          ? current.filter((j) => !allIndices.includes(j))
          : Array.from(new Set([...current, ...allIndices])),
      };
    });

  if (pending && commitSteps) {
    return (
      <Card padding="lg">
        <div className="space-y-4">
          <h3 className="text-heading-sm font-medium tracking-tight">Importando…</h3>
          <ProgressSteps steps={commitSteps} />
        </div>
      </Card>
    );
  }

  return (
    <Card padding="lg">
      <header className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div className="space-y-1">
          <h3 className="text-heading-sm font-medium tracking-tight">
            Previsualización de importación
          </h3>
          <p className="text-xs text-stone">
            {source && (
              <Badge tone="stone" size="sm" className="mr-2">
                {sourceLabel(source)}
              </Badge>
            )}
            Selecciona qué quieres traer a tu universo.
          </p>
        </div>
        <Badge tone="leaf" dot>
          {totalSelected} de {totalRows} elegidas
        </Badge>
      </header>

      <div className="relative mb-4">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-stone pointer-events-none"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filtrar filas…"
          className="w-full h-10 pl-9 pr-3 rounded-input bg-canvas border border-ink/10 focus:border-ink focus:outline-none text-sm transition-colors duration-180"
        />
      </div>

      <div className="space-y-3 max-h-[60vh] overflow-y-auto">
        {filtered.map((section) => {
          const sec = section as ImportPreviewSection & {
            _filteredRows?: { row: Record<string, unknown>; i: number }[];
          };
          const visibleRows = sec._filteredRows
            ? sec._filteredRows
            : sec.rows.map((row, i) => ({ row, i }));
          const indices = visibleRows.map((r) => r.i);
          const current = selection[sec.key] ?? [];
          const allSelected =
            indices.length > 0 && indices.every((i) => current.includes(i));
          const someSelected = !allSelected && indices.some((i) => current.includes(i));
          const open = openSections.has(sec.key);
          return (
            <div
              key={sec.key}
              className="rounded-card bg-surface border border-ink/[0.06] overflow-hidden"
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <CheckboxBox
                  state={allSelected ? "checked" : someSelected ? "indeterminate" : "empty"}
                  onClick={() => toggleAllSection(sec.key, indices)}
                  ariaLabel={`Seleccionar todas las filas de ${sec.label}`}
                />
                <button
                  type="button"
                  onClick={() => toggleSection(sec.key)}
                  aria-expanded={open}
                  className="flex-1 flex items-center justify-between gap-3 text-left"
                >
                  <div className="min-w-0 flex items-center gap-2">
                    <h4 className="font-medium text-ink">{sec.label}</h4>
                    <Badge tone="stone" size="sm">
                      {current.length}/{sec.rows.length}
                    </Badge>
                  </div>
                  <ChevronDown
                    size={16}
                    className={cn(
                      "text-stone transition-transform duration-180",
                      open && "rotate-180",
                    )}
                  />
                </button>
              </div>
              <AnimatePresence initial={false}>
                {open && (
                  <motion.ul
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.24, ease: [0.2, 0.8, 0.2, 1] }}
                    className="divide-y divide-ink/5 border-t border-ink/5"
                  >
                    {visibleRows.map(({ row, i }) => {
                      const isSelected = current.includes(i);
                      return (
                        <li key={i}>
                          <button
                            type="button"
                            onClick={() => toggleRow(sec.key, i)}
                            aria-pressed={isSelected}
                            className={cn(
                              "w-full flex items-start gap-3 px-4 py-3 text-left transition-colors duration-180 ease-pirsch",
                              isSelected ? "bg-canvas" : "hover:bg-canvas/60",
                            )}
                          >
                            <CheckboxBox
                              state={isSelected ? "checked" : "empty"}
                              ariaLabel={`Fila ${i + 1}`}
                            />
                            <div className="min-w-0 flex-1">
                              <div
                                className={cn(
                                  "text-sm leading-snug",
                                  isSelected ? "text-ink" : "text-stone",
                                )}
                              >
                                {sec.summarize(row)}
                              </div>
                              {sec.sublabel?.(row) && (
                                <div className="text-xs text-stone mt-0.5">
                                  {sec.sublabel(row)}
                                </div>
                              )}
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </motion.ul>
                )}
              </AnimatePresence>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <p className="text-sm text-stone text-center py-6">
            Ninguna fila coincide con "{query}".
          </p>
        )}
      </div>

      <div className="mt-5 flex items-center justify-end gap-2 border-t border-ink/5 pt-4">
        {onCancel && (
          <Button variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        )}
        <Button
          loading={pending}
          disabled={totalSelected === 0 && !pending}
          onClick={() => void onCommit(selection)}
          leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
        >
          {pending ? "Importando" : `${commitLabel} (${totalSelected})`}
        </Button>
      </div>
    </Card>
  );
}

function CheckboxBox({
  state,
  onClick,
  ariaLabel,
}: {
  state: "checked" | "indeterminate" | "empty";
  onClick?: () => void;
  ariaLabel: string;
}) {
  return (
    <span
      role={onClick ? "checkbox" : undefined}
      aria-checked={state === "checked" ? true : state === "indeterminate" ? "mixed" : false}
      aria-label={ariaLabel}
      onClick={(e) => {
        if (!onClick) return;
        e.stopPropagation();
        onClick();
      }}
      className={cn(
        "shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-md border transition-all duration-180 ease-pirsch select-none",
        onClick && "cursor-pointer",
        state === "checked" && "bg-ink border-ink text-canvas",
        state === "indeterminate" && "bg-ink border-ink text-canvas",
        state === "empty" && "border-ink/20 bg-canvas",
      )}
    >
      {state === "checked" && <Check size={12} strokeWidth={3} />}
      {state === "indeterminate" && (
        <span aria-hidden className="block w-2 h-0.5 bg-canvas rounded" />
      )}
    </span>
  );
}

function sourceLabel(source: NonNullable<ImportPreviewTableProps["source"]>): string {
  switch (source) {
    case "linkedin-dma":
      return "LinkedIn · DMA";
    case "linkedin-brightdata":
      return "LinkedIn · Bright Data";
    case "linkedin-zip":
      return "LinkedIn · ZIP";
    case "pdf":
      return "PDF";
    case "github":
      return "GitHub";
  }
}
