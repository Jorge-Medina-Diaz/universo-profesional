import { motion } from "motion/react";
import {
  Award,
  Briefcase,
  Check,
  FileStack,
  FolderGit,
  Sparkles,
  X,
  Zap,
} from "lucide-react";

/**
 * Dark-styled lookalikes of the app's REAL generative-UI cards (ProposalCard,
 * FormCard, DiaryCard, QuestionnaireCard, PdfImportCard, nudge chips) for the
 * landing's scripted demos. Pure presentation — every state arrives via props
 * from the replay scripts; nothing here talks to a backend.
 *
 * Anatomy mirrors src/chat/cards/* faithfully (header icon + kind badge +
 * confidence, field kinds, Confirmar/Editar/Rechazar, chips) so the landing
 * shows the product, not an illustration of it.
 */

const EASE = [0.2, 0.8, 0.2, 1] as const;

const KIND_META: Record<string, { icon: typeof Briefcase; label: string; color: string }> = {
  experience: { icon: Briefcase, label: "Experiencia", color: "#ffda6e" },
  project: { icon: FolderGit, label: "Proyecto", color: "#00d4aa" },
  skill: { icon: Zap, label: "Skill", color: "#6ece9d" },
  achievement: { icon: Award, label: "Logro", color: "#ffda6e" },
};

export function CardShell({
  children,
  delay = 0,
}: {
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, ease: EASE, delay }}
      className="rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel-raised)] p-4 shadow-[0_8px_30px_-12px_rgba(0,0,0,0.5)]"
    >
      {children}
    </motion.div>
  );
}

/** Mirror of ProposalCard: kind badge + confidence + fields + HITL actions. */
export function LandingProposalCard({
  kind,
  title,
  fields,
  confidence = "Alta",
  confirmed,
  delay = 0,
}: {
  kind: keyof typeof KIND_META;
  title: string;
  fields: [string, string][];
  confidence?: string;
  confirmed?: boolean;
  delay?: number;
}) {
  const meta = KIND_META[kind] ?? KIND_META.skill;
  const Icon = meta.icon;
  return (
    <CardShell delay={delay}>
      <div className="flex items-center gap-2.5 mb-3">
        <span
          className="grid h-8 w-8 place-items-center rounded-full shrink-0"
          style={{ background: `${meta.color}1f`, color: meta.color }}
        >
          <Icon size={14} />
        </span>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span
              className="text-[10px] font-medium px-2 py-0.5 rounded-full"
              style={{ background: `${meta.color}24`, color: meta.color }}
            >
              {meta.label}
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--cos-fill-strong)] text-[var(--cos-stone)]">
              Confianza: {confidence}
            </span>
          </div>
          <p className="text-[13px] font-medium text-[var(--cos-ink)] truncate mt-1">{title}</p>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-3">
        {fields.map(([k, v]) => (
          <div key={k} className="min-w-0">
            <dt className="text-[10px] uppercase tracking-wide text-[var(--cos-faint)]">{k}</dt>
            <dd className="text-[12px] text-[var(--cos-ink)] truncate">{v}</dd>
          </div>
        ))}
      </dl>
      {confirmed ? (
        <div className="flex items-center gap-1.5 text-[12px] text-[#6ece9d]">
          <Check size={13} /> Guardado en tu memoria
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-[12px] px-3 py-1.5 rounded-full bg-[#6ece9d] text-[#0a0a0a] font-medium">
            <Check size={12} /> Confirmar
          </span>
          <span className="text-[12px] px-3 py-1.5 rounded-full border border-[var(--cos-hairline)] text-[var(--cos-stone)]">
            Editar
          </span>
          <span className="inline-flex items-center gap-1 text-[12px] px-2.5 py-1.5 rounded-full text-[var(--cos-faint)]">
            <X size={12} /> Rechazar
          </span>
        </div>
      )}
    </CardShell>
  );
}

/** Mirror of PdfImportCard review state: parse stats + per-item confidence. */
export function LandingImportCard({
  items,
  delay = 0,
}: {
  items: { title: string; detail: string; confidence: "Alta" | "Media" | "Revisar"; checked: boolean }[];
  delay?: number;
}) {
  const tone = { Alta: "#6ece9d", Media: "#ffda6e", Revisar: "#f87171" } as const;
  return (
    <CardShell delay={delay}>
      <div className="flex items-center gap-2 mb-3">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-[var(--cos-fill-strong)] text-[var(--cos-ink)]">
          <FileStack size={14} />
        </span>
        <div>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--cos-fill-strong)] text-[var(--cos-stone)]">
            Importar · CV en PDF
          </span>
          <p className="text-[13px] font-medium text-[var(--cos-ink)] mt-1">
            12 experiencias · 34 skills · 6 proyectos
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-2 mb-3">
        {items.map((it) => (
          <div key={it.title} className="flex items-center gap-2.5">
            <span
              className={`grid h-5 w-5 place-items-center rounded-full border shrink-0 ${
                it.checked
                  ? "bg-[#6ece9d] border-transparent text-[#0a0a0a]"
                  : "border-[var(--cos-hairline)] text-transparent"
              }`}
            >
              <Check size={11} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[12px] text-[var(--cos-ink)] truncate">{it.title}</p>
              <p className="text-[10px] text-[var(--cos-faint)] truncate">{it.detail}</p>
            </div>
            <span
              className="text-[10px] px-2 py-0.5 rounded-full shrink-0"
              style={{ background: `${tone[it.confidence]}22`, color: tone[it.confidence] }}
            >
              {it.confidence}
            </span>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[12px] px-3.5 py-1.5 rounded-full bg-[#ffda6e] text-[#14130f] font-medium">
          Añadir 47
        </span>
        <span className="text-[10px] text-[var(--cos-faint)]">Solo lo dudoso ⌄</span>
      </div>
    </CardShell>
  );
}

/** Mirror of the composer nudge chip — the proactive invitation. */
export function LandingNudgeChip({ label, delay = 0 }: { label: string; delay?: number }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE, delay }}
      className="inline-flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-full border border-[#00d4aa]/40 bg-[#00d4aa]/10 text-[var(--cos-ink)]"
    >
      <Sparkles size={12} className="text-[#00d4aa]" />
      {label}
    </motion.span>
  );
}

/** Agent / user message bubbles for the scripted theaters. */
export function AgentMsg({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE, delay }}
      className="self-start max-w-[92%] rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-panel)] px-3.5 py-2.5 text-[12.5px] leading-relaxed text-[var(--cos-ink)]"
    >
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-[#00d4aa] mr-2 align-middle" />
      {children}
    </motion.div>
  );
}

export function UserMsg({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE, delay }}
      className="self-end max-w-[88%] rounded-2xl bg-[var(--cos-fill-strong)] px-3.5 py-2.5 text-[12.5px] leading-relaxed text-[var(--cos-ink)]"
    >
      {children}
    </motion.div>
  );
}
