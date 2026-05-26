/**
 * Notes listing with inline create/edit.
 *
 * Notes are markdown blobs the agent creates when the user shares narrative
 * content (learning threads, opinions, ongoing context). Same data model
 * exposed manually here.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import {
  Trash2,
  ArrowLeft,
  MessageSquare,
  Plus,
  Pencil,
  X,
  Save,
  Search,
  RefreshCw,
} from "lucide-react";
import { notes, type NoteRow } from "@/shared/api";
import { usePullToRefresh } from "@/shared/usePullToRefresh";
import { queryKeys } from "@/shared/queryKeys";
import {
  Badge,
  Button,
  Card,
  ChipInput,
  EmptyState,
  Field,
  Input,
  MarkdownEditor,
  PageHeader,
  Reveal,
  Skeleton,
  Stagger,
  Surface,
  cn,
  toast,
} from "@/ui";

interface Draft {
  id?: string;
  title: string;
  body_md: string;
  tags: string[];
}

const EMPTY_DRAFT: Draft = { title: "", body_md: "", tags: [] };

export function NotesPage() {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: queryKeys.notes.all, queryFn: () => notes.list() });
  const [draft, setDraft] = useState<Draft | null>(null);
  const [search, setSearch] = useState("");

  const create = useMutation({
    mutationFn: () =>
      notes.create({
        title: draft!.title || undefined,
        body_md: draft!.body_md,
        tags: draft!.tags,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notes.all });
      setDraft(null);
      toast.success("Nota creada");
    },
    onError: (e: unknown) => toast.error("No pudimos crear la nota", (e as Error).message),
  });

  const patch = useMutation({
    mutationFn: () =>
      notes.patch(draft!.id!, {
        title: draft!.title || null,
        body_md: draft!.body_md,
        tags: draft!.tags,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.notes.all });
      setDraft(null);
      toast.success("Nota actualizada");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos actualizar", (e as Error).message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => notes.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.notes.all }),
  });

  const items = useMemo(() => {
    const all = query.data ?? [];
    if (!search.trim()) return all;
    const q = search.trim().toLowerCase();
    return all.filter((n) => {
      const hay = `${n.title ?? ""} ${n.body_md} ${n.tags.join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
  }, [query.data, search]);

  const isEditing = draft !== null;
  const isNew = isEditing && !draft.id;
  const pending = create.isPending || patch.isPending;
  const canSave = isEditing && draft.body_md.trim().length > 0;

  const startNew = () => setDraft({ ...EMPTY_DRAFT });
  const startEdit = (n: NoteRow) =>
    setDraft({ id: n.id, title: n.title ?? "", body_md: n.body_md, tags: [...n.tags] });
  const submit = () => {
    if (!canSave) return;
    if (isNew) create.mutate();
    else patch.mutate();
  };

  const { pulling, progress } = usePullToRefresh(() => {
    qc.invalidateQueries({ queryKey: queryKeys.notes.all });
  });

  return (
    <Surface width="md" spacing="md">
      {pulling && (
        <div className="fixed top-0 inset-x-0 z-50 flex justify-center pointer-events-none">
          <div
            className="bg-canvas border border-hairline shadow-soft rounded-full p-2 mt-2"
            style={{ transform: `translateY(${Math.min(progress * 40, 40)}px)` }}
          >
            <RefreshCw
              size={16}
              className={progress >= 1 ? "animate-spin text-leaf" : "text-stone"}
            />
          </div>
        </div>
      )}
      <PageHeader
        eyebrow="Narrativa"
        title="Notas"
        subtitle="Aprendizajes, opiniones, threads en marcha. Las crea el agente cuando le cuentas algo libre — o tú directamente aquí."
        actions={
          <>
            <Button
              variant="ghost"
              onClick={() => (window.location.hash = "#/")}
              leadingIcon={<ArrowLeft size={14} />}
            >
              Chat
            </Button>
            <Button onClick={startNew} leadingIcon={<Plus size={14} />}>
              Nueva nota
            </Button>
          </>
        }
      />

      <AnimatePresence>
        {isEditing && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <Card padding="lg" tone="surface">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-heading-sm font-medium tracking-tight">
                  {isNew ? "Nueva nota" : "Editar nota"}
                </h2>
                <button
                  onClick={() => setDraft(null)}
                  aria-label="Cerrar editor"
                  className="w-8 h-8 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="space-y-4">
                <Field label="Título (opcional)">
                  {(p) => (
                    <Input
                      {...p}
                      value={draft.title}
                      onChange={(e) =>
                        setDraft({ ...draft, title: e.target.value })
                      }
                      placeholder="Sin título"
                    />
                  )}
                </Field>
                <Field label="Contenido" hint="Markdown soportado" required>
                  {(p) => (
                    <MarkdownEditor
                      {...p}
                      value={draft.body_md}
                      onChange={(v) => setDraft({ ...draft, body_md: v })}
                      placeholder="Cuéntame qué has aprendido, qué opinas, en qué andas pensando…"
                      rows={10}
                    />
                  )}
                </Field>
                <Field label="Tags" hint="Enter o coma para añadir">
                  {(p) => (
                    <ChipInput
                      {...p}
                      value={draft.tags}
                      onChange={(tags) => setDraft({ ...draft, tags })}
                      placeholder="aprendizaje, rust, RAG…"
                      tone="leaf"
                    />
                  )}
                </Field>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="ghost" onClick={() => setDraft(null)}>
                    Cancelar
                  </Button>
                  <Button
                    disabled={!canSave}
                    loading={pending}
                    onClick={submit}
                    leadingIcon={<Save size={14} />}
                  >
                    {pending ? "Guardando" : isNew ? "Crear nota" : "Guardar"}
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {(query.data?.length ?? 0) > 0 && (
        <Reveal>
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-stone pointer-events-none"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar en tus notas…"
              className="w-full h-10 pl-9 pr-3 rounded-input bg-black/[0.04] focus:bg-black/[0.06] outline-none text-sm transition-colors duration-180 border border-transparent focus:border-ink"
            />
          </div>
        </Reveal>
      )}

      {query.isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} padding="lg" className="space-y-3">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3.5 w-full" />
              <Skeleton className="h-3.5" style={{ width: `${70 - i * 10}%` }} />
            </Card>
          ))}
        </div>
      )}

      {!query.isLoading && (query.data ?? []).length === 0 && !isEditing && (
        <Card padding="lg">
          <EmptyState
            icon={<MessageSquare size={24} />}
            title="Todavía no hay notas"
            description='Cuéntale al agente algo como "estas semanas he estado investigando RAG" y se creará la primera nota automáticamente. O créala tú aquí.'
            action={
              <Button onClick={startNew} leadingIcon={<Plus size={14} />}>
                Crear primera nota
              </Button>
            }
            secondaryAction={
              <Button
                variant="outline"
                onClick={() => (window.location.hash = "#/")}
                leadingIcon={<MessageSquare size={14} />}
              >
                Ir al chat
              </Button>
            }
          />
        </Card>
      )}

      {items.length > 0 && (
        <Stagger className="flex flex-col gap-3 md:gap-4" delayStep={0.03}>
          {items.map((n) => (
            <NoteCard
              key={n.id}
              note={n}
              onEdit={() => startEdit(n)}
              onDelete={() => remove.mutate(n.id)}
            />
          ))}
        </Stagger>
      )}

      {search && items.length === 0 && (query.data?.length ?? 0) > 0 && (
        <Card padding="md" className="text-center">
          <p className="text-sm text-stone">
            Sin notas que contengan "{search}".
          </p>
        </Card>
      )}
    </Surface>
  );
}

function NoteCard({
  note,
  onEdit,
  onDelete,
}: {
  note: NoteRow;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card padding="lg" className="group">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 space-y-1.5">
          {note.title && (
            <h3 className="font-medium text-ink leading-tight">{note.title}</h3>
          )}
          {note.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {note.tags.map((t) => (
                <Badge key={t} tone="leaf" size="sm">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            aria-label="Editar nota"
            className={cn(
              "w-8 h-8 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors duration-180",
            )}
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={onDelete}
            aria-label="Eliminar nota"
            className="w-8 h-8 inline-flex items-center justify-center rounded-full text-stone hover:text-red-600 hover:bg-red-50 transition-colors duration-180"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      <p className="text-sm whitespace-pre-wrap text-ink leading-relaxed">
        {note.body_md}
      </p>
      <div className="text-xs text-stone mt-3 pt-3 border-t border-ink/5">
        {new Date(note.updated_at).toLocaleString()}
      </div>
    </Card>
  );
}
