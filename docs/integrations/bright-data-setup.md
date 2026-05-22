# Bright Data — LinkedIn Profile Web Scraper API

Path PRO interino (mientras se aprueba el trámite DMA oficial). Es el proveedor
más completo del mercado para datos de LinkedIn vía URL pública, y el más
estable (empresa B2B con 10+ años de track record, a diferencia de
Proxycurl/NinjaPear que se rebautizan cada año).

## Por qué Bright Data y no otros

Después de la sunset de Proxycurl en mayo 2026, el panorama de "LinkedIn URL
→ perfil completo" quedó así:

| Proveedor | Completitud | Legal | Estabilidad | Coste | Apto B2C |
|---|---|---|---|---|---|
| Bright Data (Web Scraper API) | ★★★★★ | Datos públicos agregados (HiQ vs LinkedIn 2022) | ★★★★★ | $0.50-1 fresh / $0.10 cached | ✓ |
| People Data Labs | ★★★☆☆ | Datos públicos agregados | ★★★★☆ | $0.10/cached | ✓ |
| Apify (LinkedIn actors) | ★★★★☆ | Zona gris | ★★★☆☆ | $5/1000 | ⚠ |
| NinjaPear (era Proxycurl) | ★★☆☆☆ — no acepta LinkedIn URL | OK | ★★☆☆☆ | $0.09/lookup | ✗ |

## Setup

### 1. Crea cuenta

1. Vete a https://brightdata.com/cp/signup
2. Sign up con email empresarial (en dev vale tu hotmail, en prod cambia a
   email del dominio de tu empresa para que te aprueben las features
   avanzadas más rápido)
3. Confirma email
4. Bright Data te asigna un **Account Manager** humano que llama/escribe en
   1-2 días. Es un B2B con onboarding personal — no esperes auto-aprobación.
   Diles que es un SaaS B2C de gestión de perfil profesional y quieres el
   **LinkedIn Profile Web Scraper API** (sync, no datasets bulk).

### 2. Activa el Web Scraper API

Tras la llamada con el AM:

1. Dashboard → **Web Scrapers** → busca `LinkedIn People Profile (by URL)`
2. Activa el dataset, te dan un `dataset_id` (formato `gd_XXXXXXXXXX`)
3. Account → **API Tokens** → genera un token (formato UUID largo)

### 3. Inyectar las credenciales

Edita el `.env` de la raíz del repo (NO commitear):

```bash
BRIGHTDATA_API_KEY=<tu-token>
BRIGHTDATA_DATASET_ID=gd_XXXXXXXXXX
```

Restart backend:

```bash
docker compose up -d --force-recreate backend
```

Verifica que el status endpoint lo detecta:

```bash
curl http://localhost:8000/api/v1/integrations/linkedin/status
# Esperado: brightdata.configured: true
```

### 4. Probar end-to-end

1. En la UI, pasa a tier PRO (Settings → "Pasar a PRO (dev)")
2. /connections → sección "Sincronizar perfil completo · PRO · global"
3. Pega tu URL pública de LinkedIn → "Importar (PRO)"
4. ~30-60 s de procesado (Bright Data hace lookup fresco la primera vez)
5. Banner verde con counts → "Importar todo"

## Pricing real para tu SaaS

Bright Data ofrece dos modos:

| Modo | Coste por lookup | Velocidad | Cuándo usar |
|---|---|---|---|
| **Fresh** | ~$0.50-1.00 | 30-60 s | Primera vez que sincronizas a un usuario |
| **Cached** | ~$0.10 | <5 s | Re-syncs del mismo perfil |

Para tu SaaS con 1000 usuarios/mes (asumiendo 1 fresh al onboarding + 2
cached al mes), son ~$0.70 × 1000 = **$700/mes**. Es caro.

**Mitigación**: una vez aprueben el DMA de LinkedIn (gratis), todos los
usuarios EEA dejan de pasar por Bright Data. Solo los usuarios fuera de la
UE seguirán pagando este coste. Si tu mercado es España/UE, deberías llegar
a <100 lookups Bright Data al mes en régimen.

## Limitaciones conocidas

- Latencia primera petición: ~60 s. El frontend muestra spinner con mensaje
  "Buscando perfil — puede tardar hasta 1 minuto" durante la espera.
- Bright Data puede fallar si la URL apunta a un perfil privado o si LinkedIn
  les bloquea temporalmente. El cliente captura estos casos y muestra un
  error claro al usuario (HTTP 502 con `detail: brightdata_failed`).
- Algunos campos (Acerca de, recomendaciones) solo aparecen si el perfil
  los tiene públicos. Si están vacíos en el resultado es porque el usuario
  no los tiene visibles para no-conexiones, no porque Bright Data falle.

## Si Bright Data te rechaza o el AM no contesta

- **Plan B inmediato**: People Data Labs (https://peopledatalabs.com).
  Self-serve, 100 lookups/mes gratis permanentes, key en 5 min.
  Menos completo pero suficiente para empezar.
- **Plan C**: pivotar todo el path PRO a Apify y aceptar la zona gris legal.
- **Plan D**: cancelar el path PRO, dejar solo DMA + ZIP, ahorrarse el
  coste y la complejidad. Si tu mercado es 90% EEA, esto es perfectamente
  viable.
