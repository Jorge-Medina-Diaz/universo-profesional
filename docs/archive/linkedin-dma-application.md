# LinkedIn Member Data Portability (3rd Party) — Solicitud paso a paso

> **Estado del trámite (sprint 3):** PAUSADO.
>
> El producto se ha pivotado a un modelo chat-first agéntico (Agno + AG-UI).
> La captura primaria es la conversación + ZIP export; importadores LinkedIn
> son secundarios. DMA sigue siendo el path "gratuito y oficial" deseable a
> largo plazo, pero el coste/tiempo del trámite (Company Page + super-admin +
> DPIA + revisión LinkedIn ~6-12 semanas) supera el ROI frente al chat-first
> que ya funciona sin él. Tramitar cuando: (1) >1.000 usuarios EEA pidan más
> que ZIP/Bright Data, o (2) un cliente B2B (recruiter, agencia) lo exija
> contractualmente. La guía a continuación queda como referencia para
> reanudar el trámite sin redescubrirla.

LinkedIn DMA es la API oficial que permite a un usuario portar SUS DATOS
a un servicio de terceros que él elige. Es el path **definitivo**, gratuito
y legal para traer perfiles completos a tu SaaS.

Cobertura: usuarios EEA (Espacio Económico Europeo) inicialmente. LinkedIn
ha anunciado expansión a UK + Suiza para 2026 H2; resto del mundo TBA.

## Prerequisitos antes de solicitar

1. **Empresa registrada** (SL/SA/SAS/Ltd) con CIF/VAT/Companies House #
2. **LinkedIn Company Page** de tu empresa
3. **Tu cuenta personal vinculada como Super-Admin** de esa Company Page
4. **App registrada** en LinkedIn Developer Platform
5. **Privacy Policy + ToS** publicados en URL pública con las cláusulas
   específicas que LinkedIn exige (templates abajo)
6. **DPIA** (Data Protection Impact Assessment) si procesas a escala. No
   obligatorio en la solicitud inicial pero LinkedIn lo puede pedir después.

## Pasos exactos

### 1. Company Page

1. https://www.linkedin.com/company/setup/new/
2. Rellena: nombre = "Universo Profesional" (o como llames tu SaaS), tagline,
   industry = "Software Development", company size, type = "Privately held",
   tipo de cuenta = "Brand"
3. Sube logo + cover
4. Verificación de la Company Page → Settings de la Page → "Manage admins"
   → "Verify ownership" → LinkedIn pide email del dominio
   (`hi@tu-dominio.com`) + a veces docs de empresa. Tarda 2-3 días.

### 2. App en Developer Platform

1. https://www.linkedin.com/developers/apps/new
2. **App name**: Universo Profesional
3. **LinkedIn Page**: selecciona la Company Page creada en paso 1
4. **App logo**: sube el mismo logo
5. Acepta los términos
6. Pestaña **Auth** → toma nota del Client ID + Client Secret
   (los meterás en `.env` cuando la app esté aprobada)
7. **Auth → Redirect URLs**: añade
   - Dev: `http://localhost:8000/api/v1/auth/linkedin/callback`
   - Dev: `http://localhost:8000/api/v1/integrations/linkedin/dma/callback`
   - Prod: lo que toque

### 3. Pedir el producto Member Data Portability

1. En la app → **Products** tab
2. Busca **"Member Data Portability (3rd Party)"** — NO el "1st Party"
   (ese es para apps personales, no para SaaS)
3. Click "Request access"
4. Formulario — usa los templates de abajo
5. Submit
6. LinkedIn responde por email en 1-4 semanas

## Templates para la solicitud

### Caso de uso (campo "Describe your use case")

```
Universo Profesional is a B2C SaaS that helps individuals build, maintain
and use a structured professional knowledge base ("their professional
universe"): experiences, education, skills, certifications, projects,
honors and career preferences. From this knowledge base, users generate
tailored CVs in minutes for specific job applications.

We use LinkedIn Member Data Portability so that each user — at their
explicit request — can import their own LinkedIn data into Universo
Profesional. This is strictly member-initiated portability per Article 6(1)
of the EU Digital Markets Act: the member ports their data from one service
they use (LinkedIn) to another they choose (us).

Scope of data requested:
- Profile (headline, summary, location, current position)
- Positions / work experience
- Education
- Skills
- Languages
- Certifications
- Projects
- Honors and awards
- Publications
- Patents
- Courses
- Volunteering experience

How we use the data:
- One-time import per member-initiated sync into the member's own
  Universo Profesional account.
- The data is shown to the member, who can edit, delete or augment any
  field before persisting it.
- Members can re-sync on demand to refresh; we never poll LinkedIn
  autonomously.
- Used internally to generate the member's own CVs / portfolios / career
  artifacts.

What we do NOT do:
- We do NOT resell, share or transfer LinkedIn data to third parties.
- We do NOT use LinkedIn data for advertising, lead generation, recruiting
  searches, competitive intelligence or market research.
- We do NOT build aggregate datasets across members.
- We do NOT contact other LinkedIn members based on imported data.

Retention: while the member's Universo Profesional account is active. On
account deletion, full hard-delete within 30 days (GDPR Art. 17). Members
can also revoke the LinkedIn connection at any time, which immediately
disables further syncs but leaves their already-imported data in their
own universe.
```

### Privacy Policy — cláusulas específicas LinkedIn

Añade estas cláusulas (o equivalentes) en tu Privacy Policy pública. La
URL de la policy se la das a LinkedIn en el formulario.

```markdown
## LinkedIn data import

If you choose to import data from LinkedIn (via "Connect LinkedIn" in your
account):

- We request access to your LinkedIn profile data using LinkedIn's official
  Member Data Portability API.
- LinkedIn shows you a consent screen listing the exact data categories
  before granting us access. You can decline.
- The imported data is associated only with your Universo Profesional
  account. We do not link it to any other account, member or aggregate
  dataset.
- You can edit, delete or augment any imported field. Imported items are
  marked with a "from LinkedIn" badge for traceability.
- You can disconnect LinkedIn at any time from Settings → Integrations.
  Disconnecting prevents further syncs; data already in your universe
  remains under your control.
- We do not resell, share or transfer your LinkedIn data to any third
  party. We do not use it for advertising, lead generation, recruiting or
  market research.
- On account deletion, all your data — including LinkedIn-sourced data —
  is hard-deleted within 30 days (GDPR Article 17).
- Legal basis: your explicit consent (GDPR Article 6(1)(a)) granted at
  the moment of authorization, and the contract with you to provide the
  service (GDPR Article 6(1)(b)).
```

### Terms of Service — cláusulas específicas LinkedIn

```markdown
## LinkedIn integration

By connecting your LinkedIn account to Universo Profesional, you confirm:

- You authorize Universo Profesional to import your own LinkedIn profile
  data into your Universo Profesional account, on your behalf, using
  LinkedIn's official Member Data Portability API.
- You will not import data of other LinkedIn members using this feature.
  This feature is exclusively for porting your own data.
- Universo Profesional acts as the data controller for the imported data
  once it is stored in your account, jointly with you. LinkedIn remains
  the controller for the data inside LinkedIn's systems.
- You can revoke the connection at any time from your Universo Profesional
  Settings, and additionally from LinkedIn's Account → Data privacy →
  Permitted services.
```

### Datos técnicos que el formulario suele pedir

| Campo | Respuesta |
|---|---|
| Scopes solicitados | `r_dma_portability_3rd_party openid profile email` |
| Auth flow | OAuth 2.0 Authorization Code (PKCE) |
| Redirect URIs | (los que pusiste arriba en la app) |
| Webhook URLs | None (no usamos LinkedIn webhooks) |
| Data centers / regions | EU (your hosting region) |
| Estimated MAU at launch | Honest estimate (10-100 está bien para empezar; LinkedIn no penaliza números pequeños, sí penaliza inflar) |
| Compliance contact | tu email + dirección postal |

## Mientras esperas la aprobación

- **Bright Data** cubre todos los lookups (paid path)
- **ZIP** cubre los users que prefieran no dar URL ni pagar
- **Activa `LINKEDIN_DMA_ENABLED=false`** en tu `.env` (default) — el código
  ya tiene el camino DMA implementado pero usa fixture en dev. Solo cambias
  `LINKEDIN_DMA_ENABLED=true` + pones las credenciales reales cuando
  LinkedIn apruebe, sin tocar código.

## Cuando llegue el email de aprobación

LinkedIn te enviará algo como:

> Your application for Member Data Portability (3rd Party) has been approved.
> You now have access to the following scopes: r_dma_portability_3rd_party.
> Your app is in development mode and can be tested with up to 100 members
> before requesting production access.

Pasos finales:

1. Edita `.env` raíz del repo:
   ```bash
   LINKEDIN_CLIENT_ID=86xxxxxxxxxxxx
   LINKEDIN_CLIENT_SECRET=WPL_AP1.xxxxxxxxxxxxxx
   LINKEDIN_DMA_ENABLED=true
   ```
2. `docker compose up -d --force-recreate backend`
3. Verifica `GET /api/v1/integrations/linkedin/status` → `dma.configured: true`
4. La UI ya muestra automáticamente "Sincronizar perfil · gratis · UE" sin
   el aviso de fixture, y el flow DMA OAuth funciona end-to-end.

## Si te rechazan

LinkedIn rechaza por estos motivos típicos:

| Motivo | Cómo arreglar |
|---|---|
| "Use case not aligned with member portability" | Reescribe el use case enfatizando que es member-initiated, single-member, no agregación. Quita cualquier mención a "sourcing", "lead gen", "candidates" |
| "Insufficient privacy disclosure" | Publica las cláusulas de Privacy Policy de arriba en una URL pública y vuelve a enviar |
| "Company Page not verified" | Espera a que LinkedIn verifique tu Company Page (paso 1) antes de re-enviar |
| "Multiple apps for same product" | Solo puedes tener una app activa por producto. Borra las antiguas |

Hay derecho a re-solicitud sin penalización tras corregir.

## Contacto humano

Si pasa más de 4 semanas sin respuesta, LinkedIn tiene formulario de
contacto en https://www.linkedin.com/help/linkedin/ask/api. Pon en el
asunto "Member Data Portability application follow-up" + el ID de tu app.
