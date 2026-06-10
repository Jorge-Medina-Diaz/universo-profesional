import i18n from "i18next";

/**
 * Landing copy deck — registered as its own namespace so the strings ship
 * with the landing code and never bloat the app bundle's translation tree.
 * Typographic honesty contract: anything rendered in mono must be true.
 */
const es = {
  nav: {
    product: "Producto",
    twin: "Twin en vivo",
    engine: "Motor",
    pricing: "Precios",
    login: "Iniciar sesión",
    cta: "Crear mi universo",
  },
  hero: {
    chip: "Agente nativo · Servidor MCP · UE",
    title1: "Tu carrera ahora tiene memoria.",
    title2: "Y agente propio.",
    sub: "Un grafo de conocimiento vivo de todo lo que has hecho — que se alimenta conversando, genera CVs con evidencia trazable, y responde a recruiters por ti.",
    ctaPrimary: "Crear mi universo",
    ctaDemo: "Hablar con el twin de demo",
    honesty: "Gratis para empezar · sin tarjeta · RGPD, hosting UE",
    counter: "{{nodes}} nodos · {{edges}} aristas — y creciendo",
  },
  manifesto: {
    p1: "Tu CV murió el día que lo exportaste.",
    p2: "Lo que has hecho desde entonces — los proyectos, las conversaciones, lo aprendido — vive en ningún sitio.",
    p3: "Universo Profesional es ese sitio.",
    p4: "Un grafo que crece cada semana y trabaja cuando tú no estás.",
  },
  feed: {
    eyebrow: "Alimentar",
    title: "Se alimenta hablando.",
    sub: "Nada de formularios. Carga tu historia una vez; mantenla con una conversación a la semana.",
    tabs: { day1: "Día 1", weekly: "Cada semana", interview: "La entrevista" },
    captions: {
      day1: "CV, LinkedIn, GitHub: carga pesada una sola vez — todo pasa por tu revisión.",
      weekly: "Proactivo, nunca repetitivo. Dos minutos por semana.",
      interview: "El agente entrevista; tú solo respondes.",
    },
  },
  exploit: {
    eyebrow: "Explotar",
    title: "Pega la oferta. Recibe el CV que esa oferta merece.",
    sub: "ATS-óptimo, en tu tono, en minutos — y solo con hechos tuyos. Cartas, seguimiento de candidaturas y preparación de entrevista incluidos.",
    stage1: "La oferta",
    stage2: "El análisis",
    stage3: "El documento",
    noEvidence: "sin evidencia — no lo inventaremos",
    traceable: "Cada línea, trazable a tu grafo. Nada inventado.",
    formats: "PDF · DOCX · JSON Resume · Europass",
  },
  twin: {
    eyebrow: "El twin",
    title: "El primer perfil profesional con el que se puede hablar.",
    sub: "Esto no es un vídeo. Estás hablando con el twin de un perfil de demostración, sobre la misma infraestructura que usará el tuyo. Los recruiters chatean con tu universo en tu URL — o incrustado en tu portfolio — y te dejan su contacto.",
    ledger1: "Perfil: «Vega Demo» — ficticio y etiquetado como tal",
    ledger2: "Responde solo con lo que su dueño ha curado",
    ledger3: "En primera persona · divulgación de IA visible",
    ledger4: "Tus visitantes pueden dejarte su contacto",
    q1: "¿Cuál es tu experiencia con Python?",
    q2: "¿Qué proyecto te enorgullece más?",
    q3: "¿Encajarías en un equipo de datos?",
    q4: "¿Qué no sabes hacer?",
    softCapCta: "Te gusta hablar con él. Imagina el tuyo →",
    replayBanner: "El twin de demo agotó su presupuesto de hoy. Esto es una repetición grabada.",
    offlineBanner: "Demo no disponible ahora mismo — repetición grabada.",
    emptyHint: "Pregunta lo que un recruiter preguntaría.",
  },
  pilot: {
    eyebrow: "Agente nativo",
    title: "Una sola conversación pilota toda la app.",
    sub: "Navega, rellena, genera, visualiza. El chat no es una función: es el sistema operativo de tu carrera.",
    honesty: "Secuencia simulada fiel al producto — pruébalo en la beta.",
    scenes: {
      s1: "«llévame a mis candidaturas»",
      s2: "«prepárame la entrevista del martes»",
      s3: "«¿cómo se conecta mi experiencia de datos?»",
      s4: "«apunta que hoy cerré la migración»",
    },
  },
  engine: {
    eyebrow: "El motor",
    title: "Esto no es un wrapper.",
    sub: "Un motor GraphRAG de cuatro carriles construido para una sola cosa: que nada de lo que se diga sobre ti carezca de evidencia.",
    lanes: { bm25: "BM25", dense: "denso (pgvector)", ppr: "PageRank personalizado", comm: "comunidades" },
    fusion: "fusión RRF (k=60)",
    facts: [
      "Recuperación híbrida en 4 carriles con fusión RRF (k=60)",
      "Grafo por usuario: Apache AGE + pgvector + snapshot igraph",
      "Ontología ESCO de la UE: ~3.000 ocupaciones, ~14.000 skills",
      "Aislamiento RLS por usuario en cada consulta — también en el twin público",
      "Streaming sub-segundo con prompt caching de Anthropic",
      "Twin público: 10 req/min/IP · presupuesto diario por perfil · scrub de PII",
    ],
  },
  mcp: {
    eyebrow: "MCP nativo",
    title: "Tu universo, convertido en herramientas.",
    sub: "Servidor MCP remoto con OAuth 2.1. Tu carrera deja de ser un documento y pasa a ser una capacidad de tus agentes.",
    clients: "Claude · ChatGPT · Cursor · cualquier cliente MCP",
    byok: "BYOK: trae tu propia clave",
  },
  trust: {
    eyebrow: "Confianza",
    title: "Tuyo. Demostrablemente.",
    rows: [
      { mech: "RLS multi-tenant", plain: "Cada consulta se ejecuta dentro de tu tenant. No existe un camino de código hacia los datos de otro usuario." },
      { mech: "Hosting UE · RGPD", plain: "Tus datos viven en Europa. Exportación y olvido, de serie." },
      { mech: "Curación default-deny", plain: "Tu twin solo puede hablar de lo que has marcado como público. Lo privado no llega al modelo." },
      { mech: "Exportable siempre", plain: "JSON Resume, Europass, PDF, DOCX. Sin rehenes." },
    ],
  },
  pricing: {
    eyebrow: "Precios",
    title1: "Empieza gratis.",
    title2: "Crece cuando quieras.",
    sub: "Sin tarjeta para empezar. 7 días de Premium gratis al registrarte. Cancela cuando quieras.",
    popular: "Más popular",
    forever: "para siempre",
    tiers: {
      free: {
        tagline: "Tu universo completo, gratis.",
        features: [
          "Universo de conocimiento completo",
          "Agentes de captura y descubrimiento",
          "Twin público con URL y widget",
          "3 CVs / mes · 1 carta / mes",
          "Exporta a PDF, DOCX y JSON Resume",
        ],
        cta: "Crear mi universo",
      },
      premium: {
        period: "/ mes · €89 al año",
        tagline: "Sin límites + tu agente en todas partes.",
        features: [
          "Todo lo de Free, sin límites",
          "CVs y cartas ilimitados",
          "Servidor MCP · 200 llamadas/día",
          "Analíticas del twin y leads",
          "Soporte prioritario",
        ],
        cta: "Probar 7 días gratis",
      },
      pro: {
        period: "/ mes · €179 al año",
        tagline: "Para quien vive dentro de sus agentes.",
        features: [
          "Todo lo de Premium",
          "Servidor MCP · 1.000 llamadas/día",
          "Máxima prioridad de cómputo",
          "Acceso anticipado a nuevas capas",
        ],
        cta: "Empezar con Pro",
      },
    },
  },
  closing: {
    title: "Tu universo ya existe. Solo está disperso.",
    sub: "Tráelo a un sitio. Gratis.",
    ctaPrimary: "Crear mi universo",
    ctaDemo: "Hablar con el demo otra vez",
    honesty: "Sin tarjeta · cancela cuando quieras",
  },
  faq: {
    title: "Preguntas",
    items: [
      { q: "¿Qué es un «Universo Profesional»?", a: "Un grafo de conocimiento privado con todo lo que has hecho: experiencias, proyectos, skills y sus relaciones, alimentado conversando y listo para generar documentos con evidencia." },
      { q: "¿Mis datos están seguros?", a: "Aislamiento por usuario a nivel de base de datos (RLS), hosting en la UE, RGPD, exportación y borrado completos. Tu twin solo expone lo que tú marcas como público." },
      { q: "¿Qué significa «MCP nativo»?", a: "Tu universo se publica como servidor MCP con OAuth: Claude, ChatGPT o Cursor pueden usarlo como herramientas para responder y generar por ti." },
      { q: "¿Es solo para perfiles técnicos?", a: "No. El grafo y la ontología ESCO cubren cualquier profesión: sanidad, marketing, educación, hostelería…" },
      { q: "¿Puedo exportar mis documentos?", a: "Siempre: PDF, DOCX, JSON Resume y Europass. Tus datos nunca quedan retenidos." },
    ],
  },
  footer: { demo: "perfil de demo", privacy: "Privacidad", terms: "Términos", mcpDocs: "MCP" },
};

const en: typeof es = {
  nav: {
    product: "Product",
    twin: "Live twin",
    engine: "Engine",
    pricing: "Pricing",
    login: "Sign in",
    cta: "Create my universe",
  },
  hero: {
    chip: "Agent-native · MCP server · EU",
    title1: "Your career now has a memory.",
    title2: "And an agent of its own.",
    sub: "A living knowledge graph of everything you've done — fed by conversation, generating CVs with traceable evidence, and answering recruiters on your behalf.",
    ctaPrimary: "Create my universe",
    ctaDemo: "Talk to the demo twin",
    honesty: "Free to start · no card · GDPR, EU hosting",
    counter: "{{nodes}} nodes · {{edges}} edges — and growing",
  },
  manifesto: {
    p1: "Your CV died the day you exported it.",
    p2: "Everything you've done since — the projects, the conversations, the lessons — lives nowhere.",
    p3: "Universo Profesional is that place.",
    p4: "A graph that grows every week and works while you don't.",
  },
  feed: {
    eyebrow: "Feed",
    title: "You feed it by talking.",
    sub: "No forms. Load your history once; keep it alive with one conversation a week.",
    tabs: { day1: "Day 1", weekly: "Every week", interview: "The interview" },
    captions: {
      day1: "CV, LinkedIn, GitHub: one heavy load — everything passes your review.",
      weekly: "Proactive, never repetitive. Two minutes a week.",
      interview: "The agent interviews; you just answer.",
    },
  },
  exploit: {
    eyebrow: "Exploit",
    title: "Paste the job ad. Get the CV that ad deserves.",
    sub: "ATS-ready, in your voice, in minutes — built only from your facts. Cover letters, application tracking and interview prep included.",
    stage1: "The offer",
    stage2: "The match",
    stage3: "The document",
    noEvidence: "no evidence — we won't invent it",
    traceable: "Every line traceable to your graph. Nothing invented.",
    formats: "PDF · DOCX · JSON Resume · Europass",
  },
  twin: {
    eyebrow: "The twin",
    title: "The first professional profile you can talk to.",
    sub: "This is not a video. You're talking to the twin of a demo profile, on the same infrastructure yours will use. Recruiters chat with your universe at your URL — or embedded in your portfolio — and leave you their contact.",
    ledger1: "Profile: “Vega Demo” — fictional, labeled as such",
    ledger2: "Answers only from owner-curated facts",
    ledger3: "First person · visible AI disclosure",
    ledger4: "Visitors can leave you their contact",
    q1: "What's your experience with Python?",
    q2: "Which project are you proudest of?",
    q3: "Would you fit a data team?",
    q4: "What can't you do?",
    softCapCta: "You like talking to it. Imagine yours →",
    replayBanner: "The demo twin used up today's budget. This is a recorded replay.",
    offlineBanner: "Demo unavailable right now — recorded replay.",
    emptyHint: "Ask what a recruiter would ask.",
  },
  pilot: {
    eyebrow: "Agent-native",
    title: "One conversation pilots the entire app.",
    sub: "Navigate, fill, generate, visualize. The chat isn't a feature: it's your career's operating system.",
    honesty: "Simulated sequence, faithful to the product — try it in the beta.",
    scenes: {
      s1: "“take me to my applications”",
      s2: "“prep me for Tuesday's interview”",
      s3: "“how does my data experience connect?”",
      s4: "“note that I shipped the migration today”",
    },
  },
  engine: {
    eyebrow: "The engine",
    title: "This is not a wrapper.",
    sub: "A four-lane GraphRAG engine built for one thing: nothing said about you ever lacks evidence.",
    lanes: { bm25: "BM25", dense: "dense (pgvector)", ppr: "Personalized PageRank", comm: "communities" },
    fusion: "RRF fusion (k=60)",
    facts: [
      "Hybrid retrieval across 4 lanes with RRF fusion (k=60)",
      "Per-user graph: Apache AGE + pgvector + igraph snapshot",
      "EU ESCO ontology: ~3,000 occupations, ~14,000 skills",
      "Per-user RLS isolation on every query — including the public twin",
      "Sub-second streaming with Anthropic prompt caching",
      "Public twin: 10 req/min/IP · daily per-profile budget · PII scrub",
    ],
  },
  mcp: {
    eyebrow: "Native MCP",
    title: "Your universe, turned into tools.",
    sub: "Remote MCP server with OAuth 2.1. Your career stops being a document and becomes a capability of your agents.",
    clients: "Claude · ChatGPT · Cursor · any MCP client",
    byok: "BYOK: bring your own key",
  },
  trust: {
    eyebrow: "Trust",
    title: "Yours. Provably.",
    rows: [
      { mech: "Multi-tenant RLS", plain: "Every query runs inside your tenant. There is no code path to another user's data." },
      { mech: "EU hosting · GDPR", plain: "Your data lives in Europe. Export and erasure, built in." },
      { mech: "Default-deny curation", plain: "Your twin can only speak about what you marked public. Private data never reaches the model." },
      { mech: "Always exportable", plain: "JSON Resume, Europass, PDF, DOCX. No hostages." },
    ],
  },
  pricing: {
    eyebrow: "Pricing",
    title1: "Start free.",
    title2: "Grow when you want.",
    sub: "No card to start. 7 days of Premium free on signup. Cancel anytime.",
    popular: "Most popular",
    forever: "forever",
    tiers: {
      free: {
        tagline: "Your complete universe, free.",
        features: [
          "Full knowledge universe",
          "Capture & discovery agents",
          "Public twin with URL and widget",
          "3 CVs / month · 1 letter / month",
          "Export to PDF, DOCX and JSON Resume",
        ],
        cta: "Create my universe",
      },
      premium: {
        period: "/ month · €89 a year",
        tagline: "No limits + your agent everywhere.",
        features: [
          "Everything in Free, unlimited",
          "Unlimited CVs and letters",
          "MCP server · 200 calls/day",
          "Twin analytics and leads",
          "Priority support",
        ],
        cta: "Try 7 days free",
      },
      pro: {
        period: "/ month · €179 a year",
        tagline: "For people who live inside their agents.",
        features: [
          "Everything in Premium",
          "MCP server · 1,000 calls/day",
          "Top compute priority",
          "Early access to new layers",
        ],
        cta: "Start with Pro",
      },
    },
  },
  closing: {
    title: "Your universe already exists. It's just scattered.",
    sub: "Bring it into one place. Free.",
    ctaPrimary: "Create my universe",
    ctaDemo: "Talk to the demo again",
    honesty: "No card · cancel anytime",
  },
  faq: {
    title: "Questions",
    items: [
      { q: "What is a “Professional Universe”?", a: "A private knowledge graph of everything you've done: experiences, projects, skills and their relations, fed by conversation and ready to generate evidence-backed documents." },
      { q: "Is my data safe?", a: "Per-user database-level isolation (RLS), EU hosting, GDPR, full export and erasure. Your twin only exposes what you mark as public." },
      { q: "What does “native MCP” mean?", a: "Your universe is published as an OAuth-protected MCP server: Claude, ChatGPT or Cursor can use it as tools to answer and generate on your behalf." },
      { q: "Is it only for technical profiles?", a: "No. The graph and the ESCO ontology cover any profession: healthcare, marketing, education, hospitality…" },
      { q: "Can I export my documents?", a: "Always: PDF, DOCX, JSON Resume and Europass. Your data is never held hostage." },
    ],
  },
  footer: { demo: "demo profile", privacy: "Privacy", terms: "Terms", mcpDocs: "MCP" },
};

let registered = false;

/** Idempotent: call from the landing entry; bundles ship with this chunk. */
export function registerLandingI18n() {
  if (registered) return;
  i18n.addResourceBundle("es", "landing", es, true, true);
  i18n.addResourceBundle("en", "landing", en, true, true);
  registered = true;
}

export type LandingDict = typeof es;
