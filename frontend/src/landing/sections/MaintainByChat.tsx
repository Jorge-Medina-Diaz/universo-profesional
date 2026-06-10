import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  AgentMsg,
  LandingDiaryCard,
  LandingFormCard,
  LandingImportCard,
  LandingNudgeChip,
  LandingProposalCard,
  UserMsg,
} from "@/landing/components/cards";
import { MorphingPillTabs } from "@/landing/components/MorphingPillTabs";
import { SectionHeading } from "@/landing/components/SectionHeading";
import {
  SemanticConstellation,
  type ConstellationHandle,
  type ConstellationRegion,
} from "@/landing/components/SemanticConstellation";

const REGIONS: ConstellationRegion[] = [
  { id: "exp", label: "Experiencia", color: "#ffda6e", cx: 0.32, cy: 0.3, count: 4, spread: 0.13 },
  { id: "skill", label: "Skills", color: "#6ece9d", cx: 0.68, cy: 0.42, count: 5, spread: 0.14 },
  { id: "proj", label: "Proyectos", color: "#00d4aa", cx: 0.42, cy: 0.72, count: 4, spread: 0.12 },
];

type Beat = "weekly" | "day1" | "discovery";

/** §3 v2 — Estrella 1A: maintaining your memory costs one conversation.
 *  Real generative-UI replicas; the agent ASKS, presents forms, proposes and
 *  nudges onward — proactivity on display, not data-entry. */
export function MaintainByChat() {
  const { t } = useTranslation("landing");
  const [beat, setBeat] = useState<Beat>("weekly");
  const constellation = useRef<ConstellationHandle>(null);

  useEffect(() => {
    const ignites: Record<Beat, string[]> = {
      weekly: ["proj", "skill"],
      day1: ["exp", "exp", "skill", "skill", "proj"],
      discovery: ["skill", "exp"],
    };
    const timers = ignites[beat].map((region, i) =>
      window.setTimeout(() => constellation.current?.pulseFrom(0.05, 0.5, region), 1200 + i * 420),
    );
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [beat]);

  return (
    <section id="memoria" className="py-24 md:py-32 px-5" aria-label={t("maintain.title")}>
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          eyebrow={t("maintain.eyebrow")}
          title={<span className="cos-gradient-text">{t("maintain.title")}</span>}
          subtitle={t("maintain.sub")}
          accent="#6ece9d"
        />

        <div className="mt-10 flex justify-center">
          <MorphingPillTabs
            tabs={[
              { id: "weekly", label: t("maintain.tabs.weekly") },
              { id: "day1", label: t("maintain.tabs.day1") },
              { id: "discovery", label: t("maintain.tabs.discovery") },
            ]}
            active={beat}
            onChange={(id) => setBeat(id as Beat)}
          />
        </div>

        <div className="mt-10 grid lg:grid-cols-[1.15fr_1fr] gap-8 items-stretch">
          <div
            key={beat}
            className="rounded-2xl border border-[var(--cos-hairline)] bg-[rgba(11,13,16,0.5)] p-5 flex flex-col gap-3 min-h-[480px]"
          >
            {beat === "weekly" && (
              <>
                <LandingDiaryCard
                  delay={0.1}
                  chips={[
                    { label: "Avancé en un proyecto", active: true },
                    { label: "Aprendí algo" },
                    { label: "Di una charla", active: true },
                  ]}
                  text="Cerré la migración y di una charla interna sobre data contracts"
                />
                <AgentMsg delay={1.0}>
                  Buen movimiento. La charla me interesa: ¿audiencia técnica o negocio? ¿La
                  reutilizarías como artículo? Te dejo dos detalles rápidos:
                </AgentMsg>
                <LandingFormCard
                  delay={1.8}
                  title="Sobre la charla de data contracts"
                  fields={[
                    { label: "Audiencia", kind: "select", options: ["Técnica", "Negocio", "Mixta"], selected: "Mixta" },
                    { label: "¿Cuánta gente?", kind: "scale", selected: 3 },
                  ]}
                />
                <LandingProposalCard
                  delay={2.8}
                  kind="achievement"
                  title="Charla interna: data contracts en la práctica"
                  confidence="Alta"
                  fields={[["Contexto", "Northwind · equipo plataforma"], ["Conecta con", "Spark · liderazgo"]]}
                  confirmed
                />
                <div>
                  <LandingNudgeChip delay={3.6} label="Tu memoria no tiene nada de mentoría este año, ¿hubo algo?" />
                </div>
              </>
            )}
            {beat === "day1" && (
              <>
                <UserMsg delay={0.1}>Te subo mi CV y mi export de LinkedIn.</UserMsg>
                <AgentMsg delay={0.7}>
                  Perfecto. Lo he leído entero — esto es lo que he entendido. Revisa lo dudoso
                  antes de que lo guarde:
                </AgentMsg>
                <LandingImportCard
                  delay={1.5}
                  items={[
                    { title: "Staff Data Engineer · Northwind", detail: "2022 — actual", confidence: "Alta", checked: true },
                    { title: "Senior Backend · Lumen Health", detail: "2019 — 2022", confidence: "Alta", checked: true },
                    { title: "Freelance — ¿2018?", detail: "fechas incompletas en el PDF", confidence: "Revisar", checked: false },
                    { title: "Spark · Airflow · 14 skills más", detail: "agrupadas por tema", confidence: "Media", checked: true },
                  ]}
                />
                <AgentMsg delay={2.6}>
                  Guardado. He conectado Spark con tu etapa en Northwind y la charla de PyConES.
                  ¿Seguimos con lo de freelance o lo dejamos para otro día?
                </AgentMsg>
              </>
            )}
            {beat === "discovery" && (
              <>
                <AgentMsg delay={0.1}>
                  Tu memoria dice que migraste 40 pipelines y que mentorizas a 4 personas — pero
                  no cuenta CÓMO decides qué migrar primero. Eso es criterio técnico que un CV
                  nunca recoge. ¿Me lo cuentas?
                </AgentMsg>
                <UserMsg delay={1.2}>
                  Prioricé por coste de cómputo y por dependencias: primero lo que desbloqueaba a
                  otros equipos.
                </UserMsg>
                <LandingProposalCard
                  delay={2.0}
                  kind="skill"
                  title="Priorización técnica orientada a impacto"
                  confidence="Alta"
                  fields={[["Evidencia", "Migración Northwind · 40 pipelines"], ["Tipo", "Criterio / liderazgo"]]}
                />
                <AgentMsg delay={3.0}>
                  Esto conecta tu lado de datos con liderazgo técnico — justo lo que tu memoria
                  tenía flojo. ¿Lo reflejamos también como logro con una métrica?
                </AgentMsg>
                <div>
                  <LandingNudgeChip delay={3.8} label="Añadir logro: -38% coste de cómputo" />
                </div>
              </>
            )}
          </div>

          {/* the memory, growing in sync */}
          <div className="relative rounded-2xl border border-[var(--cos-hairline)] bg-[var(--cos-fill)] min-h-[420px] overflow-hidden">
            <SemanticConstellation
              ref={constellation}
              key={beat}
              className="absolute inset-0"
              regions={REGIONS}
              intensity={0.7}
              interactive={false}
            />
            <p className="absolute bottom-3 inset-x-0 text-center text-xs text-[var(--cos-faint)]">
              {t(`maintain.captions.${beat}`)}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
