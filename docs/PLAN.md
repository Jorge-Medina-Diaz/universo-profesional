# Especificación técnica y análisis de mercado — SaaS B2C de gestión integral del ciclo de vida profesional con servidor MCP

> Documento en español. Punto de partida operativo y accionable para arrancar diseño y desarrollo del producto.

---

## A) Resumen ejecutivo

**Visión.** Construir un SaaS B2C en España, escalable a Europa, que sustituya al "CV en Word" por un **"Universo Profesional"**: un corpus estructurado, vivo y versionado de toda la trayectoria de una persona (estudios, experiencias, proyectos paralelos, emprendimientos, logros, certificados, cursos, idiomas, hard/soft skills, intereses, aspiraciones), desde el que **se generan bajo demanda** CVs y cartas adaptados a cada oferta y a los filtros ATS de cada empresa.

**Diferenciador único.** Además del SaaS web, se publicará un **servidor MCP remoto (Streamable HTTP + OAuth 2.1 con PKCE)** que permitirá a los usuarios actualizar su perfil, generar CVs personalizados y preparar aplicaciones **en lenguaje natural desde Claude Code, Codex, Cursor, ChatGPT Desktop, Windsurf, Zed y otros clientes MCP**, usando el token OAuth de su propia suscripción.

**Posicionamiento competitivo.** El mercado está saturado de "resume builders" (Zety, Kickresume, Resume.io, Enhancv) y "ATS optimizers" (Jobscan, Resume Worded) cuyo modelo de datos es **el documento, no la persona**. Los pocos que sí modelan a la persona —Teal HQ, Huntr, Careerflow, Manfred (España)— **no exponen MCP o lo hacen de forma muy limitada**. Rezi y Reactive Resume lanzaron MCP en 2025, pero su modelo sigue siendo "resume-centric" (varios resumes por usuario) y no "universe-centric" (un grafo de conocimiento profesional del que se proyectan documentos). Existe, por tanto, una ventana clara: ser **el primer "Career OS" español con interfaz nativa en agentes de IA**.

---

## B) Análisis de mercado y benchmark competitivo

### B.1 Panorámica del mercado

El mercado de herramientas de búsqueda de empleo se ha disparado con la IA generativa. Según el *2025 ATS Usage Report* de Jobscan (revisando las 500 páginas de carrera el 2 de junio de 2025), *"In 2025, we detected an ATS for 97.8% of Fortune 500 companies"*: prácticamente todas las grandes empresas filtran candidatos con un ATS. El *2026 Talent Trends Report* de Ashby (109 millones de solicitudes, 247.000 empleos, ene 2021–mar 2026) cuantifica el cuello de botella desde el lado del candidato: *"Throughout 2025, every hire required more than 300 applications on average. The average recruiter today is processing 291 applications per hire."* Y el *2024 Recruiting Metrics Report* de CareerPlug (60.000+ empresas, 10M+ solicitudes) sitúa la tasa de paso en *"The applicant-to-interview ratio in 2024 was 3%."*.

Sobre el famoso "75% de CVs rechazados automáticamente": ojo, es un mito sin respaldo empírico originado en Preptel (empresa extinta en 2013, sin metodología publicada). El estudio de Enhancv (sep-oct 2025, 25 reclutadores estadounidenses con 10+ plataformas ATS) lo desmiente directamente: *"23 (92%) said their systems do not auto-reject resumes for formatting, content, or design."* Lo que sí está respaldado es que el 88% de empleadores cree estar perdiéndose candidatos cualificados por mala visibilidad en la pila — un problema de *señal*, no de *bloqueo binario*. Esta distinción es relevante para el messaging del producto: nuestra propuesta no es "saltar un filtro ATS oculto", sino "maximizar señal específica para cada oferta".

En España, los ATS más usados son **Bizneo HR, SAP SuccessFactors, Workday, Talent Clue, Factorial y Personio** (los dos primeros y Workday dominan grandes empresas; Bizneo y Factorial son las opciones españolas con mejor cobertura en pymes; Bizneo ATS arranca alrededor de 9 €/empleado/mes).

El espacio se organiza en cuatro categorías:

1. **Resume builders puros** (Resume.io, Zety, Kickresume, Enhancv, CVMaker, OnlineCV, ResumeMaker.online, CVByAI). Plantillas + IA generativa para bullets. Precio 7–30 €/mes.
2. **ATS optimizers / matchers** (Jobscan, Resume Worded, Rezi, SkillSyncer). Scoring oferta↔CV. 19–50 €/mes (Jobscan Premium $49.95/mes o $299.40/año).
3. **Career platforms / trackers** (Teal HQ, Huntr, Simplify.jobs, Careerflow.ai, Jobright.ai, Final Round AI). Centralizan búsqueda + tracking + IA + LinkedIn optimizer. 9–30 €/mes con free tiers fuertes.
4. **Auto-apply engines** (LazyApply, LoopCV, JobCopilot, Sonara, AIApply). Aplicación masiva. 10–100 €/mes (advertencia: alto riesgo de exposición a ofertas fraudulentas y duplicados).

A esto se añade un eje vertical: **plataformas de matching basadas en perfil estructurado** (Manfred en España, Honeypot en DACH/Iberia, Joppy, Landing.Jobs en Iberia) y **builders open-source self-hosted** (Reactive Resume, OpenResume, JSON Resume).

### B.2 Tabla comparativa

| Producto | Categoría | Modelo de datos | Precio | MCP / API | Mercado | Fortalezas | Debilidades |
|---|---|---|---|---|---|---|---|
| **Teal HQ** | Career platform + builder | Múltiples resumes + job tracker | Free / Teal+ desde $13/sem o $29/mes | ❌ No MCP. Chrome ext. 4.9★ | EE.UU., global EN | Free tier fuerte, kanban tracker, Chrome ext. | Plantillas pocas, AI bullets reportados como genéricos en Trustpilot |
| **Huntr.co** | Job tracker + builder | Kanban + plantillas | $20–$40/mes | ❌ | EE.UU. | Tracker visual y limpio | Builder más básico que dedicados |
| **Simplify.jobs** | Autofill + tracker | Perfil único + autofill | Free + paid | ❌ Chrome ext. | EE.UU. | Autofill Workday/Greenhouse, gratis | AI bullets flojos |
| **Rezi.ai** | Builder + ATS optimizer | Resume-centric | $29/mes o lifetime | ✅ **MCP `api.rezi.ai/mcp` (Streamable HTTP, OAuth 2.1 + PKCE)**. Tools: `list_resumes`, `read_resume`, `write_resume` (con deep-merge) | EE.UU. | ATS-friendly, lifetime plan, **primer MCP comercial del vertical** | 9 plantillas, foco solo resume |
| **Reactive Resume** | Builder open-source | Multi-resume, schema propio v5 | Gratis (self-hosted o cloud) | ✅ **MCP `rxresu.me/mcp` (OAuth2 + DCR + PKCE + RFC 9728 + SEP-1649 server-card)**. Tools `reactive_resume_*` (list, get, patch). API-key fallback | Global, dev community | Open source MIT, MCP completo con resources/prompts, privacy-first | Sin generación adaptativa avanzada, sin tracker |
| **Kickresume** | Builder | Resume-centric | $9/sem, $179/año | ❌ | Global | 40+ plantillas, AI Writer GPT, AI Career Map/Coach | Sin ATS-deep, sin tracker |
| **Resume.io / Zety** | Builder | Resume-centric | $2.95 trial → $24.95/mes | ❌ | Global | Plantillas, marketing | Dark patterns de cobro |
| **Enhancv** | Builder, foco diseño | Resume-centric | $25/mes | ❌ | EE.UU.+EU | 15 plantillas ATS-tested 90%+ por Sovren y RChilli | Caro, sin tracker |
| **Jobscan** | ATS optimizer | Scan resume vs JD | $49.95/mes, $299.40/año | ❌ | EE.UU. | ATS detection (Workday/Greenhouse/Taleo), keyword accuracy 91% | Caro, solo análisis |
| **Resume Worded** | Resume scorer + LinkedIn optim. | Score | $19–$49/mes | ❌ | Global | LinkedIn optimizer | UI legacy |
| **Careerflow.ai** | All-in-one career copilot | Tracker + builder + LinkedIn + mock interview | Free / $23.99/mes | ❌ Chrome ext. | EE.UU. | LinkedIn-to-Resume, mock interviews, one-click optimizer | Bugs reportados, UX inconsistente |
| **Jobright.ai** | Job match + autofill | Perfil único | Freemium | ❌ Chrome ext. | EE.UU. | Match score + autofill miles ATS | Foco discovery |
| **LazyApply / LoopCV / JobCopilot** | Auto-apply masivo | Perfil único | $99–$199 one-time/mes | ⚠️ **LoopCV expone MCP server + REST API B2B** para developers | Global | Volumen | Calidad baja, riesgo scams |
| **Final Round AI** | Interview coach | — | — | ❌ | EE.UU. | Real-time mock | Fuera de scope CV |
| **JSON Resume** | Estándar open | JSON Schema v1.0.0 | Gratis | ✅ Repo `jsonresume/mcp` (TypeScript, 60★, último commit 4-May-2025) | Devs | Estándar de facto en devs | Comunidad pequeña, schema simple |
| **OpenResume** | Builder open-source | Local storage browser | Gratis | ❌ | Devs | ATS parser integrado, privacy local | Sin multi-resume, sin nube |
| **Manfred (getmanfred.com)** 🇪🇸 | Career platform + recruiting | **MAC schema JSON open-source con preferencias, objetivos, salario, ubicación** | Gratis para candidato; empresas pagan **15% del salario anual de la primera contratación** | ❌ No MCP. Sí: LinkedIn import vía API EU (Lambda OSS), sync MAC a GitHub del usuario | España + Sngular | **MAC en CC BY-SA 4.0 (591★ en GitHub), >120.000 perfiles en comunidad**, modela aspiraciones, no solo experiencia. Adopters: Manfred, Sngular, Mobivery, Sparta Commodities, Tinybird | Foco IT/tech, no es self-service del perfil para el candidato, sin MCP |
| **Joppy** 🇪🇸 | Tech matching Barcelona | Skills + preferencias | Gratis candidato | ❌ | España IT | Local, matching | Solo tech |
| **Landing.Jobs** 🇵🇹 | Tech matching Iberia | Perfil + matching | Gratis candidato | ❌ | Portugal/España | Iberia | Solo tech |
| **Honeypot.io** | Reverse-recruiting devs DACH+ES | Perfil técnico | Gratis candidato | ❌ | DACH + ES | Inversión reverse | Sin self-service builder |
| **LinkedIn** | Red profesional | Grafo propietario | Free / Premium 11–60 €/mes | ❌ MCP. Sí: Member Data Portability API en EU | Global | Ubicuidad, red | No exporta bien, no genera CV adaptado, no MCP, datos cerrados |
| **Read.cv / Polywork** | Identidad profesional minimalista | Perfil único | Era gratis | ❌ | Global | Estética | **Read.cv adquirido por Perplexity (descontinuado); Polywork pivotó/cerró. Hueco abandonado** |

### B.3 Estado del MCP en herramientas de carrera (mayo 2026)

* **Rezi** publica `https://api.rezi.ai/mcp` con OAuth 2.1 + PKCE, Streamable HTTP. Funciona con Claude Desktop, Claude Code, Codex, Cursor, Gemini CLI, Windsurf, Zed.
* **Reactive Resume** publica `https://rxresu.me/mcp` con OAuth2 + DCR + PKCE + RFC 9728 (Protected Resource Metadata) y API-key como fallback. Implementa además `/.well-known/mcp/server-card.json` (SEP-1649). Es la referencia técnica más madura.
* **JSON Resume** mantiene `jsonresume/mcp`: "actualiza tu resume mientras programas".
* **LoopCV** publica MCP server + REST API B2B para developers que construyan agentes (búsqueda de empleo, parsing, scoring, auto-apply).
* **Resume MCP** (mcp.so/server/resume-mcp/aarangop, artsume.dev, lobehub/rajg1011-resume-mcp-server) — proyectos hobby individuales en GitHub, sin OAuth ni multi-tenant.

**Conclusión clave:** El MCP en este vertical está naciendo. **Ningún competidor en el mercado español tiene MCP.** Hay dos competidores globales con MCP serio (Rezi y Reactive Resume), pero ambos siguen modelando "resumes" y no un universo profesional con aspiraciones, objetivos y matching semántico contra ofertas.

---

## C) Hueco de mercado y propuesta de valor única

Cruzando las tres dimensiones —**modelo de datos** (universo profesional vs. resume), **interfaz nativa en agentes IA** (MCP) y **mercado** (español/europeo con cumplimiento RGPD nativo)— el hueco es nítido:

1. **Nadie en España ofrece un Career OS self-service** con un modelo de datos rico que incluya aspiraciones, side-projects y emprendimientos. Manfred lo hace para tech con la MAC, pero es **plataforma de recruiting (B2B2C)**, no un SaaS B2C self-service donde el usuario es el cliente que paga.
2. **Nadie en el mundo combina MCP con un knowledge graph profesional con embeddings semánticos** para matching CV↔oferta. Rezi y Reactive Resume editan resumes vía MCP, pero no hacen generación adaptativa con scoring semántico ni mantenimiento incremental del perfil.
3. **Nadie en España compite con cumplimiento RGPD nativo** (datos en UE, encriptación at-rest, derecho al olvido y portabilidad como ciudadanos de primera clase). Los gigantes (Teal, Rezi, Jobscan) están en EE.UU.

**Propuesta de valor central:** *"Tu universo profesional, vivo y al servicio de tu carrera, accesible desde cualquier agente de IA, alojado en Europa y bajo tu control."*

**Sub-propuestas:**

* **Stop the Word-CV pain.** No editas un documento. Mantienes un grafo. Los documentos se generan bajo demanda.
* **Adaptive generation.** Pegas una URL/JD y el sistema selecciona, prioriza y reescribe del corpus solo lo relevante, ajustando tono y keywords al ATS detectado.
* **Living profile.** Recordatorios para añadir un curso, idioma, side-project. Diff visual.
* **AI-native UX.** Desde Claude Code o ChatGPT: *"añade el MBA que estoy haciendo en el IE", "genera un CV para esta oferta de Glovo", "prepárame la carta adaptada al ATS Bizneo"*.
* **Open & portable.** Export a JSON Resume, MAC de Manfred, Europass JSON-LD y PDF. Sin lock-in.

---

## D) Personas y Jobs-to-be-Done

### Persona 1 — **Laura, la senior cansada**
34, Product Manager en Madrid, 9 años repartidos en 4 empresas. Pasiva pero recibe ofertas por LinkedIn.
* **JTBD:** *"Cuando me llega una oferta interesante, quiero adaptar mi CV en 10 minutos sin reescribir desde cero, para responder rápido sin perder la noche."*
* **Pains:** Word desactualizado 2 años, no recuerda métricas de empleos antiguos.
* **Plan:** Premium. Web principal; MCP en Claude Desktop como añadido.

### Persona 2 — **Hugo, el dev IA-first**
28, Senior Backend, vive en Cursor, Claude Code y Codex.
* **JTBD:** *"Mantener mi perfil desde mi terminal y mis herramientas de IA. Cuando termino un proyecto interesante, decírselo a Claude Code y que actualice mi universo sin abrir otra app."*
* **Pains:** Odia formularios web. Quiere export JSON.
* **Plan:** Pro. Early adopter ideal y altavoz en comunidades dev.

### Persona 3 — **Marta, la career-switcher**
41, abogada pivotando a Legal Ops / Compliance tech. Máster en curso, varios cursos, un side-project.
* **JTBD:** *"Que mi perfil cuente la nueva historia que quiero, traduciendo experiencia jurídica al lenguaje tech para cada empresa diferente."*
* **Pains:** Gap entre lo que tiene y lo que quiere. Ansiedad de reescribir.
* **Plan:** Premium. Killer feature: matching semántico + IA generativa.

### Persona 4 (secundaria) — **Andrés, el recién graduado**
23, ingeniero. Poca experiencia, muchos cursos, hackathons.
* **JTBD:** *"CV decente que pase los ATS y muestre que aunque no tengo experiencia, sé cosas."*
* **Plan:** Free + ocasional Premium. Volumen, no ARPU.

---

## E) Requisitos funcionales por bounded context

### E.1 Identity & Access
* Registro email+password (Argon2id), Google OAuth, GitHub OAuth, LinkedIn OAuth.
* Verificación email obligatoria (token single-use, 24 h).
* MFA TOTP opcional (RFC 6238).
* Recuperación password con tokens 15 min.
* Sesiones JWT (access 15 min, refresh 30 días con rotación).
* Borrado de cuenta y export total RGPD (Art. 17 y 20).

### E.2 Professional Universe (core)

Agregados y entidades:
* **Person** (identity, summary, headline, photo, contacto, idiomas nativos).
* **Education**: institución, título, grado, fechas, GPA opcional, descripción, highlights, materias relevantes, flag "en curso".
* **Experience**: organización, rol, fechas, ubicación, tipo (full-time/part-time/contractor/freelance/internship), modalidad (remote/hybrid/onsite), descripción, **highlights con métricas**, **competences usadas**, **referrals**.
* **Project / Side-project / Entrepreneurship**: nombre, descripción, fechas, rol, tech stack, URL, impacto, status.
* **Achievement**: título, fecha, descripción, contexto, evidencia URL.
* **Skill**: hard/soft/tool/methodology, nivel (basic/intermediate/high/expert), años, último uso, evidencia (proyectos/experiencias).
* **Certification**: nombre, emisor, fecha, expiración, ID, URL verificación.
* **Course**: título, plataforma, fecha, duración, completado/en-curso, certificado URL.
* **Language**: ISO 639-1, nivel CEFR (A1–C2), certificación.
* **Publication / Talk / OSS contribution**: tipo, título, fecha, URL.
* **Interest / Hobby**: humanización.
* **CareerPreferences**: rol deseado, sectores, modalidad, expectativa salarial, willing-to-relocate, deal-breakers, motivaciones.
* **Goals**: corto/medio/largo plazo, narrativa para career-switchers.

Cada entidad tiene `embedding VECTOR(1536)`, `created_at`, `updated_at`, `visibility` (público/privado), `confidence` y `source` (manual/linkedin/pdf/mcp/ai-suggested). CRUD completo, versionado por evento, búsqueda full-text + semántica, sugerencias contextuales.

### E.3 Documents
* CVs: mínimo 8 plantillas ATS-friendly (referencia: Enhancv publica 15 plantillas ATS-tested con parseo del 90%+ por Sovren y RChilli; aspirar a métrica equivalente). ES/EN, A4/Letter.
* Cover letters: 4 plantillas.
* Generación: input = (job URL o JD pegada) + plantilla + tono + idioma + longitud; output = PDF + DOCX + JSON Resume + MAC JSON + Europass JSON-LD.
* Versionado: cada documento es inmutable; cambios crean nueva versión. Diff view.
* Public share link (read-only, opcional con contraseña/expiración).
* QR code para CV impreso.

### E.4 Applications (tracker ligero)
Pipeline Kanban (Saved / Applied / Phone Screen / Interview / Offer / Rejected / Withdrawn). Cada application linka a un Documento y a una Job (empresa, URL, JD parseada, salario detectado, ATS detectado). Notas, archivos, recordatorios.

### E.5 AI Generation Engine
Endpoints `generate_cv` y `generate_cover_letter`. Pipeline RAG:
1. Parse JD → extraer rol, requisitos hard/soft, keywords ATS.
2. Embed JD → recuperar top-k entidades del universo por similitud (pgvector cosine).
3. Re-rank híbrido (semántico + BM25 keyword + recencia, Reciprocal Rank Fusion).
4. LLM (Claude Sonnet 4.5 default, GPT-4o-mini draft, Mistral Large EU opcional) genera bullets adaptados.
5. Validación: schema JSON Resume + checks ATS-friendly + límite tokens.
6. Render PDF/DOCX.

BYOK opcional. En plan Free se usa Mistral con quota dura.

### E.6 MCP Server (sección I).

### E.7 Notifications & Reminders ("perfil vivo")
Recordatorios trimestrales, triggers (al añadir certificación → sugerir skills), "quarterly review" tipo retrospectiva, push web + email, opt-in granular.

### E.8 Import & Onboarding
* **LinkedIn:** import vía export CSV oficial; para usuarios UE adicionalmente vía **LinkedIn Member Data Portability API** (mismo patrón que `linkedin-api-lambda` open-source de Manfred).
* **PDF/Word:** Affinda API (parser ML maduro, 56 idiomas, 100+ campos) o fallback con `pypdf` + spaCy + LLM structured output.
* **JSON Resume / MAC / Europass JSON-LD:** import directo con validador.
* **Manual wizard:** 7 pasos guiados (5–10 min).

### E.9 Billing & Subscription
Stripe (tarjetas, SEPA, Bizum), facturas con IVA español, planes Free/Premium/Pro (ver O), trial 7 días sin tarjeta, cancelación al final de periodo con reverso a Free, prorrateo en upgrade/downgrade, dunning Stripe Smart Retries + email.

---

## F) Requisitos no funcionales

* **Seguridad.** TLS 1.3 obligatorio, HSTS preload, CSP estricta, cifrado at-rest AES-256, secret rotation, dependency scanning (Dependabot, Snyk), SAST (Bandit, Semgrep), pentest anual externo, bug bounty público.
* **Privacidad/RGPD.** Hosting UE (AWS Frankfurt o Scaleway Paris). Cifrado columna-level en datos sensibles. Privacy by design.
* **Rendimiento.** P95 < 300 ms lectura Universo; < 8 s generación CV (incluye LLM); < 3 s búsqueda semántica top-50.
* **Disponibilidad.** SLO 99.5% MVP, 99.9% v1. Multi-AZ desde día 1.
* **Observabilidad.** OpenTelemetry, Grafana Cloud EU o stack Tempo+Loki+Prometheus, structlog JSON, Sentry EU. Métricas de negocio (DAU, conversion, churn, MCP usage).
* **Accesibilidad.** WCAG 2.2 AA, navegación teclado completa, screen-reader, contraste verificado.
* **i18n.** ES (default) + EN; PT y FR en v2. `react-i18next` + keys backend.
* **Mobile-first.** Responsive total, PWA (instalable), apps nativas v2.
* **Coste por usuario activo.** Target < 1,5 €/mes infra+LLM para Free; < 4 €/mes para Premium.

---

## G) Arquitectura técnica

### G.1 Diagrama de alto nivel

```
[Web Browser (React 19 + Vite + Tailwind)]
              ⇣ HTTPS
[Cloudflare CDN EU]
              ⇣
[Native MCP clients (Claude Code, Codex, Cursor, …)]
              ⇣ HTTPS
[API Gateway / ALB]
              ⇣
┌────────────────────────────────────────────┐
│  FastAPI app (Python 3.13)                  │
│  ├── /api/v1/*       (REST)                 │
│  ├── /mcp/*          (Streamable HTTP)      │
│  ├── /.well-known/*  (RFC 9728 metadata)    │
│  └── /auth/oauth/*   (OAuth 2.1 AS)         │
└────────────────────────────────────────────┘
        ⇣           ⇣            ⇣           ⇣
[Postgres+pgvector] [Redis] [S3 EU SSE-KMS] [Arq queue]
                                                ⇣
                                          [Worker pool]
                                                ⇣
                            [LLM gateway: Anthropic/OpenAI/Mistral]
                                                ⇣
                                          [Affinda parsing]
```

* CDN: Cloudflare (edge EU).
* API: 2+ instancias FastAPI tras ALB, autoscaling por CPU.
* DB: PostgreSQL gestionado (AWS RDS Frankfurt o Scaleway DBaaS Paris) + read-replica.
* Cache: Redis (ElastiCache o Upstash EU).
* Object store: AWS S3 eu-central-1 o Scaleway Paris para PDFs (cifrado SSE-KMS).
* Queue: Arq (asyncio-native, Redis-backed) — más simple que Celery.

### G.2 Bounded contexts DDD

1. **Identity & Access.** Aggregate: `User`. Entities: `Session`, `OAuthClient`, `MFADevice`. VOs: `Email`, `HashedPassword`, `JWT`. Events: `UserRegistered`, `MFAEnabled`, `AccountDeleted`.
2. **Professional Universe.** Aggregate root: `Universe` (1 por user). Children entities: `EducationEntry`, `ExperienceEntry`, `ProjectEntry`, `SkillEntry`, `CertificationEntry`, `CourseEntry`, `LanguageEntry`, `AchievementEntry`, `InterestEntry`, `CareerPreferences`, `Goals`. VOs: `DateRange`, `SkillLevel`, `CEFRLevel`, `Money`, `Location`, `URL`. Events: `EntryAdded`, `EntryUpdated`, `UniverseImported`, `EmbeddingsRefreshed`.
3. **Documents.** Aggregate: `Document` (CV o CoverLetter), inmutable. Entity: `DocumentVersion`. VOs: `Template`, `LanguageCode`, `Tone`. Events: `DocumentGenerated`, `DocumentExported`, `DocumentShared`.
4. **Applications.** Aggregate: `Application` con `Stage`, `Note`. Linka `Document` y `Job`. Events: `ApplicationCreated`, `StageChanged`.
5. **AI Generation.** Application service. Events: `GenerationRequested/Completed/Failed`, `LLMTokensConsumed`.
6. **MCP.** Application service + OAuth 2.1 AS. Entities: `OAuthClient` (DCR), `AccessToken`, `RefreshToken`, `Scope`. Events: `MCPClientRegistered`, `MCPTokenIssued`, `MCPToolInvoked`.
7. **Billing.** Aggregate: `Subscription`. VOs: `Plan`, `BillingCycle`. Events: `SubscriptionCreated/Cancelled`, `InvoiceGenerated`, `PaymentFailed`.
8. **Notifications.** Application service. Events: `ReminderScheduled/Sent`.

### G.3 Capas Clean Architecture

```
domain/         (entidades, VOs, eventos, servicios de dominio puros) — sin imports externos
application/    (casos de uso, ports/interfaces, command/query handlers)
infrastructure/ (adaptadores: SQLAlchemy repos, S3, LLM clients, Stripe, Redis, Affinda)
interfaces/
  ├── api/      (FastAPI routers, Pydantic schemas, DI)
  ├── mcp/      (MCP tool handlers, OAuth endpoints)
  ├── workers/  (Arq tasks)
  └── cli/      (mgmt commands)
```

Dependency Rule: `domain → nada`; `application → domain`; `infrastructure → domain + application`; `interfaces → todos`.

### G.4 Estructura de carpetas backend

```
backend/
├── pyproject.toml          (uv, Ruff, Mypy strict, Pytest)
├── alembic/                (migrations)
├── src/
│   ├── shared/             (kernel: Result, EventBus, UoW interface, errors)
│   ├── identity/{domain,application,infrastructure,interfaces}/
│   ├── universe/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── interfaces/
│   │       ├── api/         # /api/v1/universe/*
│   │       └── mcp/         # tools: get_profile, update_education, …
│   ├── documents/
│   ├── applications/
│   ├── ai_generation/
│   ├── billing/
│   ├── notifications/
│   ├── mcp_server/         # OAuth 2.1 AS + tool registry + transport
│   └── main.py             # composición / DI / lifespan
├── tests/{unit,integration,e2e}/
└── docker/
```

### G.5 Estructura frontend React (Feature-Sliced Design)

```
frontend/
├── package.json (Vite, React 19, TS, Tailwind 4, shadcn/ui, TanStack Query, Zustand)
├── src/
│   ├── app/         (providers, router, layouts)
│   ├── pages/       (route components)
│   ├── widgets/     (CVPreview, UniverseEditor, JobMatcher)
│   ├── features/    (auth, universe, generate-cv, applications, billing, mcp-connect)
│   ├── entities/    (Education, Experience, Skill — modelos UI)
│   ├── shared/      (ui kit, hooks, lib, api client)
│   └── main.tsx
```

### G.6 Patrones

* **CQRS ligero**: comandos mutadores pasan por handlers que emiten eventos; queries van directas a repos optimizados.
* **Event-driven**: `EmbeddingsRefreshed` se dispara async tras cambios; suscriptores: search index, notifications.
* **Unit of Work** sobre SQLAlchemy AsyncSession.
* **Repository pattern** con interfaces en `application/ports`.
* **Multi-tenant lógico**: aunque 1 cuenta = 1 usuario, todas las tablas con `user_id` y Row-Level Security en Postgres (preparado para Teams/B2B v2).

---

## H) Modelo de datos

### H.1 Esquema lógico (PostgreSQL 16 + pgvector)

```sql
-- Identity
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT UNIQUE NOT NULL,
  password_hash TEXT,             -- Argon2id, null si solo OAuth
  email_verified_at TIMESTAMPTZ,
  display_name TEXT,
  locale TEXT DEFAULT 'es-ES',
  created_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

-- Universe (un agregado por user)
CREATE TABLE universes (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  headline TEXT,
  summary TEXT,
  photo_url TEXT,
  current_status TEXT,            -- 'open_to_offers' | 'searching_actively' | 'not_available'
  last_reviewed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Educations (estructura representativa; experiences/projects/etc análogos)
CREATE TABLE educations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  institution TEXT NOT NULL,
  degree TEXT,
  field_of_study TEXT,
  start_date DATE,
  end_date DATE,
  is_current BOOLEAN DEFAULT false,
  description TEXT,
  highlights JSONB DEFAULT '[]',
  gpa NUMERIC(4,2),
  url TEXT,
  embedding VECTOR(1536),
  source TEXT DEFAULT 'manual',
  visibility TEXT DEFAULT 'public',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON educations USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON educations (user_id);

-- CareerPreferences (1-1 con universe)
CREATE TABLE career_preferences (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  status TEXT,
  salary_min NUMERIC, salary_max NUMERIC, salary_currency CHAR(3),
  contract_types TEXT[],
  remote_preference TEXT,
  open_to_relocate BOOLEAN,
  working_areas JSONB,
  perks_must_have JSONB,
  perks_nice_to_have JSONB,
  preferred_competences TEXT[],
  discarded_competences TEXT[],
  preferred_roles TEXT[],
  discarded_roles TEXT[],
  goals TEXT
);

-- Documents (inmutables)
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  kind TEXT,                      -- 'cv' | 'cover_letter'
  template TEXT,
  language CHAR(2),
  job_id UUID,
  generated_from JSONB,           -- snapshot subset usado
  content_json JSONB,             -- JSON Resume normalizado
  pdf_url TEXT,
  docx_url TEXT,
  share_token TEXT UNIQUE,
  share_expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE jobs (
  id UUID PRIMARY KEY,
  user_id UUID,
  company_name TEXT,
  title TEXT,
  url TEXT,
  description_raw TEXT,
  description_parsed JSONB,
  ats_detected TEXT,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE applications (
  id UUID PRIMARY KEY,
  user_id UUID,
  job_id UUID REFERENCES jobs(id),
  document_id UUID REFERENCES documents(id),
  stage TEXT DEFAULT 'saved',
  notes TEXT,
  next_action_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- MCP OAuth
CREATE TABLE oauth_clients (
  client_id UUID PRIMARY KEY,
  user_id UUID,
  client_name TEXT,
  redirect_uris TEXT[],
  grant_types TEXT[],
  scopes TEXT[],
  client_secret_hash TEXT,        -- null para clientes públicos PKCE-only
  registered_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE oauth_tokens (
  token_hash TEXT PRIMARY KEY,    -- SHA-256, nunca plaintext
  user_id UUID,
  client_id UUID REFERENCES oauth_clients(client_id),
  kind TEXT,                      -- 'access' | 'refresh' | 'authorization_code'
  scopes TEXT[],
  resource_indicator TEXT,        -- RFC 8707
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);

-- Subscriptions
CREATE TABLE subscriptions (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  plan TEXT,
  status TEXT,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  current_period_end TIMESTAMPTZ,
  cancel_at TIMESTAMPTZ
);

-- RLS por tabla con user_id
ALTER TABLE educations ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation ON educations
  USING (user_id = current_setting('app.current_user_id')::UUID);
```

### H.2 Decisiones de diseño

* **Normalización vs JSONB.** Entidades principales son **tablas normalizadas** para queries + filtros + embeddings por entidad. Detalles flexibles (highlights, perks) van en **JSONB**.
* **pgvector**: HNSW index con `vector_cosine_ops`. Dimensión 1536 (OpenAI `text-embedding-3-small`) o 1024 (Cohere multilingual / Mistral Embed EU). Embeddings se calculan async tras cada update.
* **Event sourcing ligero**: tabla `domain_events` append-only `(user_id, aggregate_id, type, payload, created_at)` para auditoría y replay; no es ES puro.
* **Soft delete + retention**: `deleted_at` en users; tras 30 días, purga hard (cumple "derecho al olvido" RGPD Art. 17).

---

## I) Especificación detallada del servidor MCP

### I.1 Transporte y endpoints

* **Streamable HTTP** según MCP spec 2025-06-18 + 2025-11-25. Endpoint: `https://api.tu-saas.es/mcp`.
* SSE deprecated; no se implementa.
* Sigue **RFC 9728 (Protected Resource Metadata)**: expone `/.well-known/oauth-protected-resource` y `/.well-known/mcp/server-card.json` (SEP-1649).
* **OAuth 2.1 con PKCE obligatorio**. Soporta **DCR (RFC 7591)**.
* MCP server actúa como **Resource Server**; el authorization server vive en el mismo dominio en `/auth/oauth/*` (es válido por la spec, simplifica MVP; separable en v2).
* **Resource indicators (RFC 8707)** obligatorios en token requests para evitar token reuse cross-server.

### I.2 OAuth Authorization Server

* `/.well-known/oauth-authorization-server` (RFC 8414).
* `/auth/oauth/authorize` — redirige a login si no hay sesión; tras autorizar, devuelve authorization_code con PKCE challenge.
* `/auth/oauth/token` — intercambia code por access (1 h) + refresh (90 días con rotation).
* `/auth/oauth/register` — DCR (RFC 7591): cualquier cliente MCP puede registrarse con `client_name`, `redirect_uris`, `scope`.
* `/auth/oauth/revoke` — RFC 7009.
* Tokens hashed (SHA-256) en BBDD, **nunca en plaintext**. Tokens emitidos como JWT firmados (RS256) con `aud` = canonical URI del MCP server.

### I.3 Scopes propuestos

| Scope | Permite |
|---|---|
| `universe:read` | Leer el universo profesional |
| `universe:write` | Añadir/modificar entidades |
| `universe:delete` | Borrar entidades (consent explícito) |
| `documents:read` | Listar documentos |
| `documents:generate` | Generar nuevo CV / cover letter |
| `applications:read` | Ver tracker |
| `applications:write` | Crear/actualizar applications |
| `preferences:read` | Leer career preferences |
| `preferences:write` | Modificar career preferences |

Por defecto un cliente MCP nuevo pide `universe:read universe:write documents:generate`. Scopes destructivos requieren consent screen separado.

### I.4 Tools MCP expuestas

| Tool | Input | Output | Side effects | Scopes |
|---|---|---|---|---|
| `get_profile` | `{ section?: "all"|"education"|"experience"|… }` | JSON con la sección | Read | `universe:read` |
| `get_universe_summary` | `{}` | Resumen: headline, top skills, last roles, languages, status | Read | `universe:read` |
| `add_education` | `{ institution, degree, field, start, end?, is_current?, description?, highlights? }` | Entity creada | Insert + embedding refresh async | `universe:write` |
| `update_education` | `{ id, patch }` | Entity actualizada | Update + embedding refresh | `universe:write` |
| `delete_education` | `{ id }` | `{ deleted: true }` | Soft delete | `universe:delete` |
| `add_experience` | `{ organization, role, start, end?, location?, modality?, description?, highlights?, competences? }` | Entity | Insert + embedding | `universe:write` |
| `update_experience` | `{ id, patch }` | Entity | Update + embedding | `universe:write` |
| `add_project` | `{ name, description, start, end?, tech_stack?, url?, role? }` | Entity | Insert + embedding | `universe:write` |
| `add_skill` | `{ name, category, level, evidence_refs?: [entity_ids] }` | Entity | Insert + embedding | `universe:write` |
| `add_certification` / `add_course` / `add_language` / `add_achievement` | análogo | Entity | Insert + embedding | `universe:write` |
| `list_skills` | `{ category?, min_level? }` | Array | Read | `universe:read` |
| `set_career_preferences` | `{ status?, salary_min?, salary_max?, remote_preference?, contract_types?, … }` | Preferences actualizadas | Update | `preferences:write` |
| `match_job_to_profile` | `{ job_url? \| job_description? }` | `{ match_score: 0-100, gaps, strengths, suggested_keywords }` | Read + LLM | `universe:read` |
| `generate_cv` | `{ job_url?, job_description?, template_id?, language: "es"|"en", tone?, length?: "1-page"|"2-page" }` | `{ document_id, pdf_url, docx_url, json_resume }` | Crea documento, consume cuota LLM | `universe:read documents:generate` |
| `generate_cover_letter` | `{ job_url? \| description, language, tone, company_intent? }` | `{ document_id, pdf_url, content_md }` | Crea documento, LLM | `universe:read documents:generate` |
| `suggest_profile_updates` | `{}` | `[{ suggestion, reason, evidence }]` | Read + LLM | `universe:read` |
| `list_documents` | `{ limit?, kind? }` | Array | Read | `documents:read` |
| `get_document` | `{ id }` | Documento + URL | Read | `documents:read` |
| `track_application` | `{ company, title, url?, stage, document_id?, notes? }` | Application | Insert | `applications:write` |
| `import_from_pdf` | `{ file: bytes, source_name? }` | `{ candidates: [...] }` (no commit) | Llama Affinda, no escribe | `universe:write` |

### I.5 Resources MCP

* `universe://summary` — resumen JSON del universo del user actual.
* `universe://education`, `universe://experience`, etc. — listas.
* `documents://recent` — últimos 10 documentos.
* `schema://json-resume` — schema JSON Resume v1.0.0.
* `schema://mac` — schema MAC v0.6 de Manfred (interoperabilidad).

### I.6 Prompts MCP predefinidos

* `update_my_profile_after_project` — "Acabo de terminar un proyecto. Entrevístame brevemente para añadirlo al universo con todos los detalles relevantes."
* `prepare_application_for` — orquesta `match_job_to_profile` → `generate_cv` → `generate_cover_letter` → `track_application`.
* `quarterly_review` — "Revisa mi universo, identifica gaps y propón actualizaciones."

### I.7 Rate limiting y anti-abuse

* Per-token: 100 tool calls/min, 1.000/h, 10.000/día. Backoff exponencial en 429.
* `generate_cv` / `generate_cover_letter`: cuota separada según plan.
* IP-based en `/authorize`, `/token`, `/register`: 30/min.
* Logs de cada invocación `(user_id, client_id, tool_name, latency, tokens_consumed)`.
* Alertas en patrones anómalos (spike `delete_*`, ratio errores, IP rotation).

### I.8 Distribución / instalación

Docs `/docs/mcp` con instrucciones por cliente:

* **Claude Desktop / Claude Code**: `claude mcp add --transport http tu-saas https://api.tu-saas.es/mcp` → browser para OAuth.
* **Codex (OpenAI)**: `codex mcp add tu-saas https://api.tu-saas.es/mcp`.
* **Cursor**: entrada en `.cursor/mcp.json`.
* **Windsurf / Zed**: config análoga.
* **Sin DCR / fallback**: Personal Access Token + `Authorization: Bearer` header.

---

## J) Flujos clave paso a paso

### J.1 Onboarding completo (objetivo < 10 minutos)
1. Sign-up email o Google. Verificación email.
2. Pantalla bienvenida con 3 vías de import: LinkedIn, PDF, "empezar de cero".
3. Si LinkedIn → user descarga ZIP de "Get a copy of your data" → drag&drop → mapping automático → revisión side-by-side de cada sección.
4. Si PDF → upload → Affinda parsing → revisión.
5. Wizard 3 pasos finales: preferencias de carrera, top-skills, headshot opcional.
6. Pantalla "Universo creado": grafo visual con counts y "tu primer CV está a un click".
7. Generar primer CV: URL/JD demo → ~8 s → PDF descargable.
8. CTA "Conecta tu Claude Code" con deep-link.

### J.2 Generar CV adaptado a oferta (web)
1. Click "New CV" → pega URL o JD plana.
2. Backend: scraping Playwright sandbox 8 s; fallback JD pegada.
3. LLM #1 barato (Mistral / GPT-4o-mini): parsing JD → schema `{role, seniority, hard_skills, soft_skills, must_haves, nice_to_haves, ats_keywords, company_signals}`.
4. Embed JD chunks → query pgvector top-K=30 por sección.
5. Re-rank híbrido (Reciprocal Rank Fusion: semántico + BM25 + recencia).
6. LLM #2 (Claude Sonnet 4.5): "Aquí JD parseada + subset relevante del universo. Genera CV JSON Resume con bullets adaptados, manteniendo veracidad, optimizando para keywords ATS, idioma {language}, tono {tone}, longitud {length}."
7. Validación Pydantic + JSON Schema.
8. Render: HTML Jinja2 → WeasyPrint (PDF); python-docx (DOCX). Storage S3 cifrado.
9. UI: preview side-by-side, "regenerar sección X" granular.
10. Guarda Document, ofrece tracking en Applications.

### J.3 Mantenimiento incremental vía MCP desde Claude Code
1. Usuario abre Claude Code. Sesión MCP autenticada (refresh token vigente).
2. Usuario: *"Acabo de terminar un proyecto open source de un MCP server para Kubernetes. Añádelo a mi perfil."*
3. Claude llama `add_project` con `{name: "k8s-mcp-server", description: "...", tech_stack: ["Go", "Kubernetes"], url: "...", role: "creator"}`.
4. Server inserta + job async (embedding + sugerir skills relacionados).
5. Claude llama `suggest_profile_updates` → detecta "Go" no estaba en skills.
6. Claude pregunta al usuario, llama `add_skill {name: "Go", category: "hard", level: "intermediate", evidence_refs: [project_id]}`.
7. Confirmación textual.

### J.4 Conexión OAuth de un cliente MCP nuevo
1. Usuario en Codex: `codex mcp add tu-saas https://api.tu-saas.es/mcp`.
2. Codex hace GET; recibe 401 + `WWW-Authenticate: Bearer resource_metadata="https://api.tu-saas.es/.well-known/oauth-protected-resource"`.
3. Codex fetch PRM → descubre auth server.
4. Codex POST `/auth/oauth/register` (DCR) con `client_name`, `redirect_uris=["http://127.0.0.1:PORT/callback"]`.
5. Codex abre browser en `/auth/oauth/authorize?client_id=...&response_type=code&code_challenge=...&scope=universe:read+universe:write+documents:generate&resource=https://api.tu-saas.es/mcp`.
6. Usuario login + consent screen ("Codex pide acceso a leer/escribir tu universo y generar documentos").
7. Redirect a callback con `code`. Codex POST `/auth/oauth/token` con `code_verifier` → access (1 h) + refresh.
8. Codex guarda tokens en keyring local.
9. Llamadas posteriores: `Authorization: Bearer <token>` con `aud=https://api.tu-saas.es/mcp`.

---

## K) Plan de seguridad y privacidad

* **Hosting UE obligatorio.** Recomendación primaria: **AWS Frankfurt (eu-central-1)** por madurez de servicios gestionados y certificaciones (ISO 27001, SOC 2, BSI C5). Alternativas: **Scaleway Paris** (soberanía francesa, candidato SecNumCloud para sensibilidad alta), **Hetzner Falkenstein** (coste óptimo, FRA/HEL). Evitar transferencias a EE.UU. más allá de las imprescindibles para LLMs.
* **Datos en reposo cifrados**: AES-256 en RDS, S3 SSE-KMS, KMS keys con rotación anual. Para campos especialmente sensibles (CV completo, datos especiales como discapacidad declarada), columna-level encryption con `pgcrypto` y clave per-user derivada.
* **Datos en tránsito**: TLS 1.3 obligatorio, HSTS preload 1 año, certificados Let's Encrypt o AWS ACM.
* **Secretos**: AWS Secrets Manager o Doppler. Nunca en código. Rotación trimestral.
* **Compliance RGPD (Reglamento UE 2016/679 + LOPDGDD Ley Orgánica 3/2018):**
  * **Bases legales**: consentimiento explícito (Art. 6.1.a) para datos profesionales + ejecución contrato (Art. 6.1.b) para servicio.
  * **Registro de actividades de tratamiento** (Art. 30).
  * **DPO**: para tratamiento sistemático masivo de datos personales en SaaS B2C se recomienda nombrar DPO externo desde día 1. Según *delegadoprotecciondatos.com*, *"generalmente oscila entre 600 € y 3.600 € anuales para PYMEs"*; presupuestar dentro de ese rango en fase MVP.
  * **Evaluación de Impacto (EIPD/DPIA)** antes del lanzamiento por scoring automatizado (matching, embeddings).
  * **Derechos ARCO-POL** (Acceso, Rectificación, Cancelación/Supresión, Oposición, Portabilidad, Limitación) self-service vía API + UI. Plazo de respuesta máximo 1 mes.
  * **Notificación de brechas**: protocolo 72 h a AEPD; comunicación a afectados si alto riesgo (Art. 33-34).
  * **Transferencias internacionales**: si se usan LLMs en EE.UU. (Anthropic/OpenAI), incluir SCC actualizadas + considerar la EU–US Data Privacy Framework (con riesgo legal Schrems II) + ofrecer **opción "EU-only" con Mistral Large hospedado en Francia** como toggle de usuario.
  * **Retención**: datos activos mientras la cuenta esté viva; al borrar cuenta, hard delete a 30 días excepto logs financieros (4 años fiscales) y logs de seguridad (1 año).
* **LSSI-CE (Ley 34/2002)**: info legal completa, política de cookies con CMP (Cookiebot/OneTrust o el módulo OSS de PostHog), T&C aceptados en registro.
* **Edad mínima** 16 años (Art. 7 LOPDGDD), declarativa con checkbox + bloqueo de re-registro tras incumplimiento detectado.

---

## L) Roadmap por fases

### MVP (Sprint 1-8, ~4 meses, equipo 2 backend + 1 frontend + 0,5 designer + 0,5 PM)

**Entra:**
* Identity completo (email+password, Google OAuth, verificación email).
* Universe CRUD web (educations, experiences, projects, skills, certifications, courses, languages).
* Import LinkedIn ZIP + PDF (Affinda).
* Generación CV adaptado (1 template ATS + 1 creativo), idiomas ES/EN, PDF + DOCX.
* Export JSON Resume.
* MVP MCP con 8 tools core (`get_profile`, `add_*`/`update_*` para 5 entidades, `generate_cv`, `match_job_to_profile`), OAuth 2.1 + PKCE + DCR, Streamable HTTP.
* Billing Stripe Free + Premium.
* RGPD: aviso, política, export, borrado.

**No entra:** Applications tracker, Cover letters, multi-template, recordatorios, mobile app, equipos.

**Métricas éxito:** 500 usuarios registrados, 50 Premium, 20 conexiones MCP activas, NPS > 30.

### v1 (mes 5-8)
* Cover letters generator.
* Applications tracker Kanban.
* Recordatorios "perfil vivo".
* 6 plantillas adicionales (3 ATS, 3 creativas).
* Onboarding wizard mejorado con video.
* Spanish i18n completo.
* Web push.
* Export Europass JSON-LD + MAC JSON (interop Manfred).
* Pipeline IA mejorado, BYOK opcional.
* MCP: tools applications + `suggest_profile_updates`.

### v2 (mes 9-14)
* Mobile app (React Native con Expo).
* Plan Pro con prioridad LLM y export ilimitado.
* Match contra job boards (InfoJobs, LinkedIn Jobs vía partners o scraping responsable).
* Integración Calendly/Google Calendar.
* Public profile/portfolio pages (`tu-saas.es/u/laura-perez`).
* Análisis de salario contra mercado español (data partner: Manfred Salary Guide).
* B2B Lite: dashboard para coaches/career advisors multi-cliente.
* Multi-idioma: PT, FR, IT, DE.

---

## M) Riesgos principales y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| LinkedIn limita aún más export/API | Alta | Medio | CSV oficial + Member Data Portability API EU; modelo agnóstico de import |
| OpenAI/Anthropic suben precios o cambian rate limits | Media | Alto | Multi-provider (Anthropic, OpenAI, Mistral); BYOK; caché; finetuning de modelos pequeños en v2 |
| MCP spec cambia (es joven) | Alta | Medio | Implementar tras spec 2025-11-25 (estable), seguir grupo Auth biweekly, abstracción de transporte |
| Competidor (Teal, Rezi, Manfred) lanza MCP+Universe español | Media-Alta | Alto | First-mover en ES+MCP, schema open-source compatible MAC, integración Manfred no competencia |
| Brecha GDPR | Baja | Catastrófico | Cifrado + pentest + bug bounty + DPO + seguro ciber |
| Adopción MCP lenta entre no-técnicos | Alta | Bajo | MCP es feature opcional; UI web es path principal |
| Coste Affinda alto al escalar | Media | Medio | Negociación de contrato; parser propio LLM con structured output en v2 |
| Comoditización por LLMs directos ("ya le pido a Claude que me haga el CV") | Alta | Alto | Defensibility = corpus persistente + matching semántico + ATS knowledge + integración bidireccional, no la prompt-engineering |
| Confusión con auto-apply | Media | Bajo | Mensaje claro: no aplicamos por ti, optimizamos artillería |
| Inspección AEPD | Baja | Alto | DPO + registro tratamientos + EIPD documentada |

---

## N) Stack tecnológico final recomendado

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | **React 19 + Vite + TypeScript** | Decisión del usuario; tooling rápido; ecosistema |
| UI | **shadcn/ui + Tailwind CSS 4** | Componentes accesibles, copy-paste, themable |
| Frontend state | **TanStack Query + Zustand** | Server cache + UI state |
| Forms | **React Hook Form + Zod** | Validación isomórfica |
| Backend | **FastAPI 0.115+ (Python 3.13)** | Decisión; async-first; OpenAPI gratis |
| ORM | **SQLAlchemy 2.0 async + Alembic** | Estándar; migrations |
| Validación | **Pydantic v2** | Performance Rust, integración FastAPI |
| Auth | **Authlib + python-jose** | OAuth 2.1 / OIDC compliant; JWT |
| MCP SDK | **mcp (oficial Anthropic Python)** o **FastMCP** | Maduro mayo 2026 |
| BBDD | **PostgreSQL 16 + pgvector 0.8** | Relacional + vectorial; HNSW |
| Embeddings | **OpenAI text-embedding-3-small** (1536) o **Mistral Embed** (1024, EU) | Coste/calidad; multilingual |
| Cache & sessions | **Redis 7** | Rate limit, session, queue backend |
| Task queue | **Arq** | Async-native, más simple que Celery |
| Object storage | **AWS S3 (eu-central-1)** o **Scaleway Paris** | SSE-KMS, versioning |
| PDF | **WeasyPrint** | Fidelidad CSS, sin Chrome headless |
| DOCX | **python-docx** + plantilla | Compatibilidad Word máxima |
| Resume parsing | **Affinda API** + fallback LLM structured output | Accuracy top, 56 idiomas, 100+ campos |
| LLM | **Anthropic Claude Sonnet 4.5** default; **GPT-4o** alternativo; **Mistral Large (París)** EU-only opcional | Multi-provider, resiliencia, soberanía |
| Scraping | **Playwright + asyncio + Browserless** | JD scraping diverso |
| Email transac. | **Postmark (EU)** o **Brevo (FR)** | Deliverability, RGPD-friendly |
| Pagos | **Stripe** (entidad española) | Bizum, IVA, dunning |
| Observabilidad | **OpenTelemetry + Grafana Cloud EU + Sentry EU** | Trazas + logs + errores |
| CI/CD | **GitHub Actions + Docker + Kamal o ECS Fargate** | Simple, reproducible |
| IaC | **Terraform + Terragrunt** | Drift control, multi-env |
| Testing | **Pytest + Playwright Test + Vitest + Schemathesis** | API + E2E |
| Lint/format | **Ruff + Mypy strict + ESLint + Prettier + Biome** | Calidad alta |
| Feature flags | **Unleash self-hosted** o **PostHog EU** | Rollouts graduales |
| Product analytics | **PostHog EU** | RGPD-friendly, replay opt-in |

---

## O) Modelo de negocio sugerido

### Planes (precios IVA incluido España)

| Plan | Precio | Para quién | Universo | CVs/mes | Cover letters/mes | MCP | LLM | Otros |
|---|---|---|---|---|---|---|---|---|
| **Free** | 0 € | Probadores, estudiantes | Ilimitado | 3 | 1 | ❌ | Mistral barato | 1 plantilla ATS, watermark "Generated with…" |
| **Premium** | **9,99 €/mes o 89 €/año** | Buscador activo | Ilimitado | Ilimitado | Ilimitado | ✅ con cuota (200 calls/día) | OpenAI o Mistral | 8 plantillas, sin watermark, applications tracker, export JSON/Europass/MAC, recordatorios |
| **Pro** | **19,99 €/mes o 179 €/año** | Power user, devs IA-first, switchers | Ilimitado | Ilimitado, prioridad | Ilimitado | ✅ sin cuota (1.000 calls/día) | Claude Sonnet 4.5 default | Todo Premium + BYOK + match scoring detallado + soporte prioritario |

**Trial:** 7 días Premium gratis sin tarjeta.

**Política MCP:** Acceso al servidor MCP es **Premium+**. Justificación: (a) clientes MCP típicos son power users con willingness-to-pay alto, (b) el coste LLM por invocación es significativo, (c) crea un wedge claro contra Reactive Resume (gratis pero sin matching ni generación adaptativa avanzada).

### Costes target por usuario activo
* Free: ~0,40 €/mes (infra prorrateada + embeddings limitados).
* Premium: ~2,80 €/mes (LLM + parsing + infra) → margen 72%.
* Pro: ~5,50 €/mes (Claude default + más tokens) → margen 72%.

### Métricas año 1
* 8.000 free signups, 12% conversion = 960 paying.
* MRR mes 12: ~10.000 € (mix Premium/Pro 80/20, ARPU ~12 €).
* Churn < 6%/mes (sticky por universo persistente).
* CAC < 25 € vía SEO técnico, X/LinkedIn dev community, partnerships bootcamps.

### GTM España
1. **Launch en Product Hunt + Hacker News + r/cscareerquestionsEU + DEV.to** — angle: "First Career OS native to AI agents".
2. **Open-source el schema** (compatibilidad con MAC de Manfred) → credibilidad técnica + SEO.
3. **Partnerships**: bootcamps (Ironhack, 4Geeks, Le Wagon), universidades (IE, IESE, UPM, UPC), comunidades dev (Madrid DevOps, BarcelonaJS, PyConES).
4. **Content SEO**: "Cómo pasar el ATS de Bizneo / SAP SuccessFactors / Workday", "CV en español para tech 2026", "JSON Resume tutorial", "Configura MCP en Claude Code para tu carrera".
5. **Posicionamiento Manfred-friendly**: complemento, no competencia. *"Manfred te conecta con empresas; nosotros te preparamos el universo profesional listo y exportable."*

---

## Recomendaciones finales (decision-ready)

1. **Empieza por el MCP antes que por las plantillas bonitas.** Es tu wedge defensible. Las plantillas hay miles; un MCP serio con OAuth 2.1 + DCR + Resource Indicators y un schema rico no.
2. **Adopta MAC de Manfred como interlingua y posiciónate como complemento, no rival.** Manfred es la única plataforma con un schema open-source rico y una comunidad de 120.000+ profesionales tech en España. Compatibilidad bidireccional con su MAC te da credibilidad técnica gratis y un canal potencial.
3. **No prometas "automatic apply".** Los datos lo confirman (Ashby: 291 aplicaciones por contratación en 2025) — el problema no es volumen, es señal. El mensaje "calidad sobre cantidad, generación adaptativa con tu universo real" diferencia.
4. **Hostea en UE desde día 1 y comunica el RGPD como producto, no como afterthought.** Es un genuino diferenciador para Personas 1 y 3 (no-técnicos preocupados por la privacidad).
5. **MVP en 4 meses con foco brutal**: universe CRUD + import + 1 generador + MCP con 8 tools + Stripe + RGPD. Lanza en β cerrada en comunidades dev españolas; itera 8 semanas más antes de marketing masivo.
6. **Mide adopción MCP como métrica núcleo desde el primer día**: % de Premium con al menos 1 cliente MCP conectado, tool invocations/usuario/semana. Es tu indicador principal de retention futuro porque es un hábito que recompra automáticamente.

**Benchmarks que cambiarían las decisiones:**
* Si la conversión Free→Premium se queda < 6% durante 3 meses, recortar el límite del Free (de 3 a 1 CV/mes) o introducir un *paywall MCP* desde mes 2.
* Si los clientes MCP siguen siendo < 5% de Premium después del v1, plantear hacer el MCP disponible en Free con cuota dura para ampliar el TAM del wedge.
* Si Manfred o Rezi lanzan algo equivalente en ES antes del v1, ejecutar pivote rápido a "agency-mode" (Persona 3 + coaches B2B Lite v2 antes).

---

## Caveats

* El MCP spec evolucionó rápidamente entre 2025-03 y 2025-11; la spec 2025-11-25 es la más reciente al cierre de esta especificación (mayo 2026) y es estable, pero hay extensiones en draft (Client ID Metadata Documents SEP-991, Server-Side Authorization Management SEP-1299) que conviene seguir.
* La cifra del "75% de CVs rechazados por ATS" que circula masivamente en marketing del sector **no tiene base empírica** y conviene no usarla en messaging. La realidad estadística sólida es: (a) ~97,8% de Fortune 500 usan algún ATS (Jobscan 2025), (b) ~3% de aplicantes llegan a entrevista (CareerPlug 2024), (c) ~291 aplicaciones por contratación (Ashby 2026). El cuello de botella real es la **señal específica para cada oferta**, no un "filtro automático binario", como confirma el estudio de Enhancv (sep-oct 2025) donde 92% de reclutadores encuestados negaron auto-rechazos por formato.
* Affinda es la opción más sólida de parsing, pero su pricing comercial requiere negociación; estimar coste real con prototipo antes de comprometerse contractualmente.
* La spec MCP recomienda separación entre Resource Server y Authorization Server. En el MVP los unimos en el mismo dominio para simplicidad — es válido por la spec, pero conviene planear la separación para v2 si se monta multi-region.
* Las cifras de adopción de MCP (Rezi, Reactive Resume) son recientes y todavía limitadas; la curva de adopción real entre usuarios no técnicos está por validar. La estrategia debe ser sólida tanto si el MCP "explota" como si se queda como feature pro de nicho.
* Las cifras de Manfred (120.000+ perfiles en su Guía Salarial 2026) son comunidad combinada Manfred + Circular; el dato más conservador del Tech Career Report más reciente registraba 112.660 perfiles. Ambos números reflejan la posición dominante de Manfred en la comunidad tech española y el porqué de la estrategia de complementariedad.
* Los precios sugeridos (9,99 €/19,99 €) están calibrados al mercado español; en mercados anglo conviene re-pricing a £8/$12 y £15/$24 respectivamente cuando se internacionalice.

---

*Documento de especificación técnica v1.0. Pensado como punto de partida operativo y accionable para arranque de desarrollo.*