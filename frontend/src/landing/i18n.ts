import i18n from "i18next";

/**
 * Landing copy deck v2 — dark cinematic, "sistema de memoria agéntica"
 * (NUNCA "grafo"/"nodos"/"aristas" — counters say recuerdos · conexiones).
 * Typographic honesty contract: anything rendered in mono must be true.
 */
const es = {
  nav: {
    memory: "Tu memoria",
    twin: "Twin en vivo",
    payoff: "Qué hace por ti",
    pricing: "Precios",
    login: "Iniciar sesión",
    cta: "Crear mi memoria",
  },
  hero: {
    chip: "Agente nativo · MCP · UE",
    title1: "Tu carrera ahora tiene memoria.",
    title2: "Y agente propio.",
    sub: "Un sistema de memoria agéntica que se alimenta conversando, te pregunta lo que importa y responde a recruiters por ti.",
    ctaPrimary: "Crear mi memoria",
    ctaDemo: "Hablar con el twin",
    honesty: "Gratis para empezar · sin tarjeta · RGPD, hosting UE",
    counter: "{{nodes}} recuerdos · {{edges}} conexiones",
    demoLabel: "así se siente — secuencia fiel al producto",
    demoHonesty: "simulación fiel",
    demo: {
      q: "Vi que lideraste la migración a Kubernetes en Northwind. ¿Qué tamaño tenía el clúster y qué fue lo más difícil?",
      a: "Unas 40 máquinas en 3 clústeres. Lo duro fue migrar sin parar producción.",
      formTitle: "Déjame guardarlo bien — 3 detalles:",
      f1: "Dimensión del clúster",
      f2: "¿Cómo desplegabais?",
      f3: "¿Cuánto te marcó este proyecto? (1-5)",
      proposalTitle: "Migración a Kubernetes sin downtime",
      p1: "Stack",
      p2: "Alcance",
      nudge: "¿Registramos también la charla que diste al equipo?",
    },
  },
  manifesto: {
    p1: "Tu CV murió el día que lo exportaste.",
    p2: "Todo lo que has hecho desde entonces vive en ningún sitio.",
    p3: "Dale a tu carrera un sistema de memoria.",
    p4: "Uno que pregunta, recuerda y trabaja cuando tú no estás.",
  },
  maintain: {
    eyebrow: "Mantenerla",
    title: "Cuesta una conversación.",
    sub: "El agente no toma notas: pregunta como un buen entrevistador, te presenta formularios ya rellenos y te invita a ampliar justo donde tu memoria tiene huecos.",
    tabs: { weekly: "Cada semana", day1: "Día 1", discovery: "Descubrimiento" },
    captions: {
      weekly: "Dos minutos. El agente convierte una frase en memoria estructurada — y repregunta lo que vale la pena.",
      day1: "Tu historia entra una sola vez: CV, LinkedIn, GitHub. Todo pasa por tu revisión, con confianza por elemento.",
      discovery: "El agente conecta lo que ya sabe y propone lo que falta. Nunca la misma pregunta dos veces.",
    },
  },
  mcp: {
    eyebrow: "Donde ya trabajas",
    title: "Tu memoria te sigue a Claude, ChatGPT o Cursor.",
    sub: "Servidor MCP nativo con OAuth. Apunta lo que haces y pregunta lo que hiciste — sin abrir la app.",
    clients: "Claude · ChatGPT · Cursor · cualquier cliente MCP",
    byok: "BYOK: trae tu propia clave",
    term: {
      cmd1: "> apunta que hoy cerré la migración y presenté al equipo de plataforma",
      tool1: "universe.capture",
      out1: "✓ 2 recuerdos guardados · 1 conexión nueva",
      cmd2: "> ¿qué hice en marzo relacionado con clientes?",
      tool2: "universe.search",
      out2: "3 evidencias: workshop con ACME · demo de la API · informe trimestral",
    },
  },
  twin: {
    eyebrow: "El twin",
    title: "El primer perfil profesional con el que se puede hablar.",
    sub: "Esto no es un vídeo. Estás hablando con el twin de un perfil de demostración sobre la misma infraestructura que usará el tuyo. Los recruiters chatean con tu memoria en tu URL — o incrustada en tu portfolio — y te dejan su contacto.",
    ledger1: "Perfil: «Vega Demo» — ficticio y etiquetado como tal",
    ledger2: "Responde solo con lo que su dueño ha decidido compartir",
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
  anatomy: {
    eyebrow: "Por dentro",
    title: "Anatomía de una respuesta.",
    sub: "Qué pasa en el segundo que separa una pregunta de una respuesta con pruebas.",
    s1q: "«¿Ha trabajado con equipos cliente?»",
    s1: "Llega la pregunta",
    s2: "Tu memoria se consulta en 4 direcciones a la vez",
    lanes: ["por palabras", "por significado", "por relaciones", "por temas"],
    s3: "Encuentra evidencias",
    ev1: { kind: "Experiencia", text: "Workshops trimestrales con clientes en Lumen Health" },
    ev2: { kind: "Proyecto", text: "Portal de soporte — 12 clientes enterprise" },
    ev3: { kind: "Logro", text: "NPS de soporte de 31 a 58 en dos trimestres" },
    s4: "Responde solo con eso",
    s4detail: "Si no hay evidencia, lo dice: «eso no lo tengo compartido». Nunca inventa.",
    techStrip: "BM25 + embeddings + PageRank personalizado + comunidades · fusión RRF · aislamiento por usuario (RLS) — reproducible en el repo",
  },
  payoff: {
    eyebrow: "El dividendo",
    title: "Lo que tu memoria hace por ti.",
    sub: "Cuando tu historia vive en un solo sitio, todo lo demás son minutos.",
    tiles: {
      cv: {
        title: "CV por oferta, con pruebas",
        body: "Pega la oferta y recibe un CV ATS-óptimo construido solo con tus hechos.",
        honesty: "sin evidencia — no lo inventaremos",
      },
      letters: { title: "Cartas en tu tono", body: "Cada afirmación, trazable a un recuerdo." },
      prep: { title: "Prep de entrevista", body: "Preguntas probables + tus historias listas." },
      tracking: { title: "Seguimiento de candidaturas", body: "Pipeline completo con match por requisito." },
    },
    formats: "PDF · DOCX · JSON Resume · Europass",
  },
  trust: {
    eyebrow: "Confianza",
    title: "Tuya. Demostrablemente.",
    rows: [
      { mech: "Aislamiento por usuario (RLS)", plain: "Tu memoria se consulta siempre dentro de tu espacio. No existe un camino de código hacia la de otra persona." },
      { mech: "Hosting UE · RGPD", plain: "Tus datos viven en Europa. Exportación y olvido, de serie." },
      { mech: "Compartir es opt-in", plain: "Tu twin solo habla de lo que marcas como público. Lo privado no llega al modelo." },
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
        tagline: "Tu memoria completa, gratis.",
        features: [
          "Sistema de memoria agéntica completo",
          "Agente proactivo de captura y descubrimiento",
          "Twin público con URL y widget",
          "3 CVs / mes · 1 carta / mes",
          "Exporta a PDF, DOCX y JSON Resume",
        ],
        cta: "Crear mi memoria",
      },
      premium: {
        period: "/ mes · €89 al año",
        tagline: "Sin límites + tu memoria en todas partes.",
        features: [
          "Todo lo de Free, sin límites",
          "CVs y cartas ilimitados",
          "Servidor MCP · 200 llamadas/día",
          "Analíticas del twin y contactos",
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
    title: "Tu memoria ya existe. Solo está dispersa.",
    sub: "Tráela a un sitio. Gratis.",
    ctaPrimary: "Crear mi memoria",
    ctaDemo: "Hablar con el twin otra vez",
    honesty: "Sin tarjeta · cancela cuando quieras",
  },
  faq: {
    title: "Preguntas",
    items: [
      { q: "¿Qué es un «sistema de memoria agéntica»?", a: "Un lugar privado donde vive todo lo que has hecho — experiencias, proyectos, habilidades y cómo se relacionan — mantenido por un agente que conversa contigo y listo para generar documentos con pruebas." },
      { q: "¿Mis datos están seguros?", a: "Aislamiento por usuario a nivel de base de datos, hosting en la UE, RGPD, exportación y borrado completos. Tu twin solo expone lo que tú marcas como público." },
      { q: "¿Qué significa «MCP nativo»?", a: "Tu memoria se conecta a Claude, ChatGPT o Cursor como herramientas: apunta lo que haces y pregunta lo que hiciste desde donde ya trabajas." },
      { q: "¿Es solo para perfiles técnicos?", a: "No. La memoria entiende cualquier profesión: sanidad, marketing, educación, hostelería…" },
      { q: "¿Puedo exportar mis documentos?", a: "Siempre: PDF, DOCX, JSON Resume y Europass. Tus datos nunca quedan retenidos." },
    ],
  },
  footer: { demo: "perfil de demo", privacy: "Privacidad", terms: "Términos", mcpDocs: "MCP" },
};

const en: typeof es = {
  nav: {
    memory: "Your memory",
    twin: "Live twin",
    payoff: "What it does",
    pricing: "Pricing",
    login: "Sign in",
    cta: "Create my memory",
  },
  hero: {
    chip: "Agent-native · MCP · EU",
    title1: "Your career now has a memory.",
    title2: "And an agent of its own.",
    sub: "An agentic memory system that feeds itself through conversation, asks what matters, and answers recruiters on your behalf.",
    ctaPrimary: "Create my memory",
    ctaDemo: "Talk to the twin",
    honesty: "Free to start · no card · GDPR, EU hosting",
    counter: "{{nodes}} memories · {{edges}} connections",
    demoLabel: "this is how it feels — faithful to the product",
    demoHonesty: "faithful simulation",
    demo: {
      q: "I saw you led the Kubernetes migration at Northwind. How big was the cluster, and what was hardest?",
      a: "About 40 machines across 3 clusters. The hard part was migrating without stopping production.",
      formTitle: "Let me store this properly — 3 details:",
      f1: "Cluster size",
      f2: "How did you deploy?",
      f3: "How defining was this project? (1-5)",
      proposalTitle: "Zero-downtime Kubernetes migration",
      p1: "Stack",
      p2: "Scope",
      nudge: "Should we also record the talk you gave the team?",
    },
  },
  manifesto: {
    p1: "Your CV died the day you exported it.",
    p2: "Everything you've done since lives nowhere.",
    p3: "Give your career a memory system.",
    p4: "One that asks, remembers, and works while you don't.",
  },
  maintain: {
    eyebrow: "Maintaining it",
    title: "Costs one conversation.",
    sub: "The agent doesn't take notes: it asks like a good interviewer, presents pre-filled forms, and invites you to expand exactly where your memory has gaps.",
    tabs: { weekly: "Every week", day1: "Day 1", discovery: "Discovery" },
    captions: {
      weekly: "Two minutes. The agent turns one sentence into structured memory — and follows up where it's worth it.",
      day1: "Your history enters once: CV, LinkedIn, GitHub. Everything passes your review, with per-item confidence.",
      discovery: "The agent connects what it knows and proposes what's missing. Never the same question twice.",
    },
  },
  mcp: {
    eyebrow: "Where you already work",
    title: "Your memory follows you into Claude, ChatGPT or Cursor.",
    sub: "Native MCP server with OAuth. Note what you do and ask what you did — without opening the app.",
    clients: "Claude · ChatGPT · Cursor · any MCP client",
    byok: "BYOK: bring your own key",
    term: {
      cmd1: "> note that I shipped the migration today and presented to the platform team",
      tool1: "universe.capture",
      out1: "✓ 2 memories saved · 1 new connection",
      cmd2: "> what did I do in March involving clients?",
      tool2: "universe.search",
      out2: "3 evidences: ACME workshop · API demo · quarterly report",
    },
  },
  twin: {
    eyebrow: "The twin",
    title: "The first professional profile you can talk to.",
    sub: "This is not a video. You're talking to the twin of a demo profile on the same infrastructure yours will use. Recruiters chat with your memory at your URL — or embedded in your portfolio — and leave you their contact.",
    ledger1: "Profile: “Vega Demo” — fictional, labeled as such",
    ledger2: "Answers only from what its owner chose to share",
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
  anatomy: {
    eyebrow: "Inside",
    title: "Anatomy of an answer.",
    sub: "What happens in the second between a question and an evidence-backed answer.",
    s1q: "“Have you worked with client-facing teams?”",
    s1: "The question arrives",
    s2: "Your memory is searched in 4 directions at once",
    lanes: ["by words", "by meaning", "by relationships", "by themes"],
    s3: "It finds evidence",
    ev1: { kind: "Experience", text: "Quarterly client workshops at Lumen Health" },
    ev2: { kind: "Project", text: "Support portal — 12 enterprise clients" },
    ev3: { kind: "Achievement", text: "Support NPS from 31 to 58 in two quarters" },
    s4: "It answers with only that",
    s4detail: "When there's no evidence, it says so: “that's not something I have shared.” It never invents.",
    techStrip: "BM25 + embeddings + personalized PageRank + communities · RRF fusion · per-user isolation (RLS) — reproducible in the repo",
  },
  payoff: {
    eyebrow: "The dividend",
    title: "What your memory does for you.",
    sub: "Once your history lives in one place, everything else takes minutes.",
    tiles: {
      cv: {
        title: "A CV per job ad, with proof",
        body: "Paste the ad, get an ATS-ready CV built only from your facts.",
        honesty: "no evidence — we won't invent it",
      },
      letters: { title: "Letters in your voice", body: "Every claim traceable to a memory." },
      prep: { title: "Interview prep", body: "Likely questions + your stories, ready." },
      tracking: { title: "Application tracking", body: "Full pipeline with per-requirement match." },
    },
    formats: "PDF · DOCX · JSON Resume · Europass",
  },
  trust: {
    eyebrow: "Trust",
    title: "Yours. Provably.",
    rows: [
      { mech: "Per-user isolation (RLS)", plain: "Your memory is always queried inside your own space. There is no code path to anyone else's." },
      { mech: "EU hosting · GDPR", plain: "Your data lives in Europe. Export and erasure, built in." },
      { mech: "Sharing is opt-in", plain: "Your twin only speaks about what you mark public. Private data never reaches the model." },
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
        tagline: "Your full memory, free.",
        features: [
          "Complete agentic memory system",
          "Proactive capture & discovery agent",
          "Public twin with URL and widget",
          "3 CVs / month · 1 letter / month",
          "Export to PDF, DOCX and JSON Resume",
        ],
        cta: "Create my memory",
      },
      premium: {
        period: "/ month · €89 a year",
        tagline: "No limits + your memory everywhere.",
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
    title: "Your memory already exists. It's just scattered.",
    sub: "Bring it into one place. Free.",
    ctaPrimary: "Create my memory",
    ctaDemo: "Talk to the twin again",
    honesty: "No card · cancel anytime",
  },
  faq: {
    title: "Questions",
    items: [
      { q: "What is an “agentic memory system”?", a: "A private place where everything you've done lives — experiences, projects, skills and how they relate — maintained by an agent that converses with you, ready to generate evidence-backed documents." },
      { q: "Is my data safe?", a: "Per-user database-level isolation, EU hosting, GDPR, full export and erasure. Your twin only exposes what you mark as public." },
      { q: "What does “native MCP” mean?", a: "Your memory connects to Claude, ChatGPT or Cursor as tools: note what you do and ask what you did, from where you already work." },
      { q: "Is it only for technical profiles?", a: "No. The memory understands any profession: healthcare, marketing, education, hospitality…" },
      { q: "Can I export my documents?", a: "Always: PDF, DOCX, JSON Resume and Europass. Your data is never held hostage." },
    ],
  },
  footer: { demo: "demo profile", privacy: "Privacy", terms: "Terms", mcpDocs: "MCP" },
};

let registered = false;

/** Idempotent. MUST run after i18n.init() (addResourceBundle only exists
 *  post-init) — call it from the component body, never at module scope. */
export function registerLandingI18n() {
  if (registered) return;
  if (typeof i18n.addResourceBundle !== "function") {
    i18n.on("initialized", () => registerLandingI18n());
    return;
  }
  i18n.addResourceBundle("es", "landing", es, true, true);
  i18n.addResourceBundle("en", "landing", en, true, true);
  registered = true;
}

export type LandingDict = typeof es;
