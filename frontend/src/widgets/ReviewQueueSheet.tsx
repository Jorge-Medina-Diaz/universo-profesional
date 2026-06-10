/**
 * ReviewQueueSheet — right slide-over listing everything that awaits the
 * user's judgement (P3.E unified inbox: pending suggestions + ESCO/dedup
 * quarantine, from GET /coherence/review-queue).
 *
 * Items don't resolve here: each row has ONE action — "Revisar en el chat" —
 * which injects a Spanish prompt referencing the item into the agent thread
 * (pendingInjection), expands the chat and closes the sheet. The agent's
 * existing card flows handle the actual accept/reject.
 *
 * Reuses vaul (the same Drawer the mobile WidgetsSheet uses) with
 * direction="right" so the slide-over keeps the app's a11y/overlay behaviour.
 */
import { Drawer } from "vaul";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Inbox, Lightbulb, MessageCircle, ShieldAlert } from "lucide-react";
import { coherence, type ReviewQueueItem } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import { useChatState } from "@/chat/state";
import { Badge, Button, Skeleton } from "@/ui";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

/** Compact Spanish relative date — "hace 5 min", "ayer", "hace 4 días". */
function formatRelative(iso: string | null): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const mins = Math.round((Date.now() - then) / 60_000);
  if (mins < 1) return "ahora mismo";
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "ayer";
  if (days < 30) return `hace ${days} días`;
  return new Date(iso).toLocaleDateString();
}

function reviewPrompt(item: ReviewQueueItem): string {
  return item.source === "quarantine"
    ? `Revisemos el elemento en cuarentena: «${item.title}». ¿Qué pasó y cómo lo resolvemos?`
    : `Revisemos la sugerencia pendiente: «${item.title}». Cuéntame de qué va y decidimos juntos.`;
}

export function ReviewQueueSheet({ open, onOpenChange }: Props) {
  const setPendingInjection = useChatState((s) => s.setPendingInjection);
  const setChatExpanded = useChatState((s) => s.setChatExpanded);

  const queue = useQuery({
    queryKey: queryKeys.coherence.reviewQueue,
    queryFn: () => coherence.reviewQueue(20),
    staleTime: 5 * 60_000,
    enabled: open,
  });

  const reviewInChat = (item: ReviewQueueItem) => {
    setPendingInjection({ content: reviewPrompt(item) });
    onOpenChange(false);
    setChatExpanded(true);
  };

  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange} direction="right">
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-40 bg-ink/30 backdrop-blur-sm" />
        <Drawer.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-canvas text-ink shadow-lift outline-none">
          <Drawer.Title className="sr-only">Pendientes de revisar</Drawer.Title>
          <header className="flex items-center justify-between border-b border-hairline px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-ink">Pendientes de revisar</h2>
              <p className="mt-0.5 text-[11px] text-stone">
                Sugerencias y elementos en cuarentena — se resuelven en el chat.
              </p>
            </div>
            {typeof queue.data?.total === "number" && queue.data.total > 0 && (
              <Badge tone="nova" size="sm">
                {queue.data.total}
              </Badge>
            )}
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-4">
            {queue.isPending && (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-20 w-full rounded-card" />
                <Skeleton className="h-20 w-full rounded-card" />
                <Skeleton className="h-20 w-full rounded-card" />
              </div>
            )}

            {queue.isError && (
              <div className="flex flex-col items-start gap-3 rounded-card border border-danger/30 bg-danger-soft px-4 py-3 text-xs text-danger-ink">
                <span className="flex items-start gap-2">
                  <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                  No pude cargar la cola de revisión: {(queue.error as Error).message}
                </span>
                <Button size="sm" variant="outline" onClick={() => queue.refetch()}>
                  Reintentar
                </Button>
              </div>
            )}

            {queue.isSuccess && queue.data.items.length === 0 && (
              <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
                <span className="grid h-10 w-10 place-items-center rounded-full bg-surface text-stone">
                  <Inbox size={18} />
                </span>
                <p className="text-sm font-medium text-ink">Nada pendiente</p>
                <p className="text-xs text-stone">
                  Cuando el motor de coherencia tenga dudas o sugerencias, aparecerán aquí.
                </p>
              </div>
            )}

            {queue.isSuccess && queue.data.items.length > 0 && (
              <ul className="flex flex-col gap-2">
                {queue.data.items.map((item) => {
                  const isQuarantine = item.source === "quarantine";
                  const when = formatRelative(item.created_at);
                  return (
                    <li
                      key={`${item.source}:${item.id}`}
                      className="rounded-card border border-ink/[0.06] bg-surface p-3 shadow-soft"
                    >
                      <div className="flex items-start gap-3">
                        <span
                          aria-hidden
                          className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${
                            isQuarantine ? "bg-danger-soft text-danger-ink" : "bg-sunbeam-soft text-sunbeam-ink"
                          }`}
                        >
                          {isQuarantine ? <ShieldAlert size={15} /> : <Lightbulb size={15} />}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-baseline justify-between gap-2">
                            <span className="truncate text-sm font-medium leading-tight text-ink">
                              {item.title}
                            </span>
                            {when && <span className="shrink-0 text-[10px] text-stone/80">{when}</span>}
                          </div>
                          <div className="mt-0.5 text-[11px] text-stone">
                            {isQuarantine ? "Cuarentena" : "Sugerencia"}
                            {item.kind ? ` · ${item.kind}` : ""}
                          </div>
                          {item.detail && (
                            <p className="mt-1 line-clamp-2 text-xs text-stone">{item.detail}</p>
                          )}
                          <div className="mt-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => reviewInChat(item)}
                              leadingIcon={<MessageCircle size={13} />}
                            >
                              Revisar en el chat
                            </Button>
                          </div>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
