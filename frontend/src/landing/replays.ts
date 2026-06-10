/** Scripted sequences for the landing's faithful simulations (§3 feed,
 *  §4 exploit, §6 agent-pilot) and the §5 twin fallback replay. Everything
 *  here is clearly framed as simulation in the UI copy — the LIVE proof is
 *  the twin itself. */

export interface FeedBeat {
  id: string;
  messages: { role: "user" | "agent" | "card"; text: string }[];
  /** constellation regions to ignite as the beat lands */
  ignite: string[];
}

interface FeedScript {
  day1: FeedBeat;
  weekly: FeedBeat;
  interview: FeedBeat;
}

const FEED_ES: FeedScript = {
  day1: {
    id: "day1",
    messages: [
      { role: "user", text: "Te subo mi CV de 2019 y mi export de LinkedIn." },
      { role: "agent", text: "Perfecto. Analizando… he encontrado 12 experiencias, 34 skills y 6 proyectos." },
      { role: "card", text: "12 experiencias · 34 skills · 6 proyectos — revisar y confirmar" },
      { role: "user", text: "Confirmo ✓" },
    ],
    ignite: ["exp", "exp", "skill", "skill", "skill", "proj", "edu"],
  },
  weekly: {
    id: "weekly",
    messages: [
      { role: "agent", text: "¿Qué has hecho esta semana?" },
      { role: "user", text: "Migré el pipeline a Kubernetes y di una charla interna sobre data contracts." },
      { role: "card", text: "+ Proyecto: migración a Kubernetes · + Logro: charla interna" },
    ],
    ignite: ["proj", "skill"],
  },
  interview: {
    id: "interview",
    messages: [
      { role: "agent", text: "Vi que usaste Terraform en ese proyecto — ¿gestionabas también el estado remoto y los workspaces?" },
      { role: "user", text: "Sí, con S3 + DynamoDB de lock, y workspaces por entorno." },
      { role: "card", text: "Skill enriquecida: Terraform — estado remoto, workspaces, locking" },
    ],
    ignite: ["skill"],
  },
};

const FEED_EN: FeedScript = {
  day1: {
    id: "day1",
    messages: [
      { role: "user", text: "Uploading my 2019 CV and my LinkedIn export." },
      { role: "agent", text: "Got it. Parsing… I found 12 experiences, 34 skills and 6 projects." },
      { role: "card", text: "12 experiences · 34 skills · 6 projects — review & confirm" },
      { role: "user", text: "Confirmed ✓" },
    ],
    ignite: ["exp", "exp", "skill", "skill", "skill", "proj", "edu"],
  },
  weekly: {
    id: "weekly",
    messages: [
      { role: "agent", text: "What have you been up to this week?" },
      { role: "user", text: "Migrated the pipeline to Kubernetes and gave an internal talk on data contracts." },
      { role: "card", text: "+ Project: Kubernetes migration · + Achievement: internal talk" },
    ],
    ignite: ["proj", "skill"],
  },
  interview: {
    id: "interview",
    messages: [
      { role: "agent", text: "I saw you used Terraform on that project — did you also manage remote state and workspaces?" },
      { role: "user", text: "Yes — S3 + DynamoDB locking, workspaces per environment." },
      { role: "card", text: "Skill enriched: Terraform — remote state, workspaces, locking" },
    ],
    ignite: ["skill"],
  },
};

export interface ExploitRequirement {
  label: string;
  level: number; // 0..1 evidence strength
  missing?: boolean;
}

interface ExploitScript {
  offerTitle: string;
  offerMeta: string;
  offerChips: string[];
  requirements: ExploitRequirement[];
  bullets: { text: string; evidence: string }[];
}

const EXPLOIT_ES: ExploitScript = {
  offerTitle: "Backend Engineer — Plataforma de pagos",
  offerMeta: "Remoto (UE) · €55–70k",
  offerChips: ["Python", "PostgreSQL", "Kubernetes", "Kafka", "Terraform", "Liderazgo"],
  requirements: [
    { label: "Python avanzado", level: 0.95 },
    { label: "PostgreSQL en producción", level: 0.85 },
    { label: "Kubernetes", level: 0.7 },
    { label: "Kafka / streaming", level: 0.6 },
    { label: "Terraform / IaC", level: 0, missing: true },
    { label: "Experiencia en pagos", level: 0, missing: true },
  ],
  bullets: [
    { text: "Lideré la migración de 40+ pipelines a Spark, reduciendo coste de cómputo un 38%", evidence: "Experiencia · Northwind" },
    { text: "Reduje la latencia p95 de 800ms a 120ms reescribiendo el agregador clínico", evidence: "Experiencia · Lumen Health" },
    { text: "Mantengo Atlas, catálogo de datos open source con 1.2k estrellas", evidence: "Proyecto · Atlas" },
  ],
};

const EXPLOIT_EN: ExploitScript = {
  offerTitle: "Backend Engineer — Payments platform",
  offerMeta: "Remote (EU) · €55–70k",
  offerChips: ["Python", "PostgreSQL", "Kubernetes", "Kafka", "Terraform", "Leadership"],
  requirements: [
    { label: "Advanced Python", level: 0.95 },
    { label: "PostgreSQL in production", level: 0.85 },
    { label: "Kubernetes", level: 0.7 },
    { label: "Kafka / streaming", level: 0.6 },
    { label: "Terraform / IaC", level: 0, missing: true },
    { label: "Payments experience", level: 0, missing: true },
  ],
  bullets: [
    { text: "Led the migration of 40+ pipelines to Spark, cutting compute cost 38%", evidence: "Experience · Northwind" },
    { text: "Cut p95 latency from 800ms to 120ms rewriting the clinical aggregator", evidence: "Experience · Lumen Health" },
    { text: "Maintain Atlas, an open-source data catalog with 1.2k stars", evidence: "Project · Atlas" },
  ],
};

export interface PilotScene {
  command: string;
  effect: "navigate" | "card" | "graph" | "diary";
  surfaceTitle: string;
  surfaceBody: string;
}

const PILOT_ES = (scenes: { s1: string; s2: string; s3: string; s4: string }): PilotScene[] => [
  { command: scenes.s1, effect: "navigate", surfaceTitle: "Candidaturas", surfaceBody: "Kanban: 3 en entrevista · 5 aplicadas · 2 ofertas" },
  { command: scenes.s2, effect: "card", surfaceTitle: "Preparación de entrevista", surfaceBody: "Brief de empresa · 12 preguntas probables · 3 historias STAR" },
  { command: scenes.s3, effect: "graph", surfaceTitle: "Universo — región de datos", surfaceBody: "Spark ↔ Airflow ↔ Northwind ↔ Atlas" },
  { command: scenes.s4, effect: "diary", surfaceTitle: "Diario", surfaceBody: "+ Logro: migración cerrada — vinculado a Kubernetes" },
];

const TWIN_REPLAY_ES = [
  { role: "user" as const, content: "¿Cuál es tu experiencia con Python?" },
  { role: "assistant" as const, content: "Llevo más de 9 años con Python: ahora mismo soy Staff Data Engineer en Northwind Analytics, donde lidero la plataforma de datos sobre Spark, y antes construí APIs clínicas con FastAPI en Lumen Health. También mantengo Atlas, un catálogo de datos open source en Python." },
  { role: "user" as const, content: "¿Qué no sabes hacer?" },
  { role: "assistant" as const, content: "Honestamente: no tengo experiencia en frontend más allá de React básico, ni en sistemas embebidos. Mi terreno es datos y backend. Si tu equipo necesita eso a fondo, no soy el perfil." },
];

const TWIN_REPLAY_EN = [
  { role: "user" as const, content: "What's your experience with Python?" },
  { role: "assistant" as const, content: "Over 9 years with Python: I'm currently a Staff Data Engineer at Northwind Analytics leading the data platform on Spark, and previously built clinical APIs with FastAPI at Lumen Health. I also maintain Atlas, an open-source data catalog in Python." },
  { role: "user" as const, content: "What can't you do?" },
  { role: "assistant" as const, content: "Honestly: no real frontend experience beyond basic React, and no embedded systems. My ground is data and backend. If your team needs those deeply, I'm not the profile." },
];

export function getReplays(lang: string) {
  const isEn = lang.startsWith("en");
  return {
    feed: isEn ? FEED_EN : FEED_ES,
    exploit: isEn ? EXPLOIT_EN : EXPLOIT_ES,
    pilot: PILOT_ES,
    twinReplay: { turns: isEn ? TWIN_REPLAY_EN : TWIN_REPLAY_ES },
  };
}
