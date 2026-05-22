/**
 * Generic confirm/cancel HITL card. Used for destructive or surprising
 * actions where the agent needs an explicit "yes" before continuing.
 *
 * Tone palette mirrors the rest of the system: leaf (safe), sunbeam (default
 * CTA), amber (warn), danger (destructive).
 */
import { type ReactNode } from "react";
import { AlertTriangle, Check, X } from "lucide-react";
import { Button, ChatMessageMotion, Badge, cn } from "@/ui";

export type ConfirmTone = "default" | "warn" | "danger";

export interface ConfirmCardProps {
  actionLabel: string;
  target: string;
  description?: ReactNode;
  payload?: Record<string, unknown> | null;
  pending?: boolean;
  tone?: ConfirmTone;
  confirmLabel?: string;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}

export function ConfirmCard({
  actionLabel,
  target,
  description,
  payload,
  pending = false,
  tone = "default",
  confirmLabel,
  onConfirm,
  onCancel,
}: ConfirmCardProps) {
  const visible = payload
    ? Object.entries(payload).filter(
        ([, v]) =>
          v !== null &&
          v !== undefined &&
          v !== "" &&
          !(Array.isArray(v) && v.length === 0),
      )
    : [];
  return (
    <ChatMessageMotion>
      <div
        role="dialog"
        aria-modal="false"
        aria-labelledby={`confirm-card-title-${target.replace(/\s/g, "-")}`}
        className={cn(
          "rounded-card bg-surface p-5 my-3 max-w-md border border-ink/[0.06] shadow-soft",
          tone === "warn" && "border-sunbeam/40",
          tone === "danger" && "border-red-200/70",
        )}
      >
        <div className="flex items-start gap-3 mb-3">
          {tone !== "default" && (
            <span
              aria-hidden
              className={cn(
                "inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0",
                tone === "warn" && "bg-sunbeam-soft text-sunbeam-ink",
                tone === "danger" && "bg-red-50 text-red-700",
              )}
            >
              <AlertTriangle size={14} />
            </span>
          )}
          <div className="min-w-0 flex-1 space-y-1">
            <Badge
              tone={tone === "danger" ? "danger" : tone === "warn" ? "amber" : "leaf"}
              size="sm"
            >
              {actionLabel}
            </Badge>
            <h4
              id={`confirm-card-title-${target.replace(/\s/g, "-")}`}
              className="font-medium text-base text-ink leading-tight"
            >
              {target}
            </h4>
          </div>
        </div>
        {description && (
          <p className="text-xs text-stone mb-3 leading-relaxed">{description}</p>
        )}
        {visible.length > 0 && (
          <dl className="text-xs space-y-1.5 mb-4 bg-canvas/60 rounded-card p-3">
            {visible.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[110px_1fr] gap-3 items-baseline">
                <dt className="text-stone font-medium capitalize truncate" title={k}>
                  {k.replace(/_/g, " ")}
                </dt>
                <dd className="text-ink break-words">
                  {Array.isArray(v)
                    ? v.join(", ")
                    : typeof v === "object" && v
                      ? JSON.stringify(v)
                      : String(v)}
                </dd>
              </div>
            ))}
          </dl>
        )}
        <div className="flex gap-2">
          <Button
            size="sm"
            loading={pending}
            variant={tone === "danger" ? "danger" : "primary"}
            onClick={() => void onConfirm()}
            leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
          >
            {pending ? "Procesando" : confirmLabel ?? actionLabel}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel} leadingIcon={<X size={14} />}>
            Cancelar
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}
