"""Curated domain templates for the `curiosity_specialist`.

When the user says something like "estoy aprendiendo ecommerce", the specialist
looks up the matching template here and passes its `sections` to
`present_deep_dive`. If the domain isn't in the dict, a generic fallback is
used instead (see `fallback_template`).

The templates are deliberately opinionated — they reflect the buckets a hiring
panel would care about for that domain. Update freely as the landscape moves;
it's a plain dict.

Section kinds (must match `DeepDiveCard.tsx`):
  - "multi_chips"   — multi-select from a fixed `options` list
  - "single_chips"  — single-select from a fixed `options` list
  - "chip_input"    — free-form multi-tag input
  - "scale"         — integer scale (defaults to 1..5)
  - "open"          — textarea
"""
from __future__ import annotations

from typing import Any


def _depth_section() -> dict[str, Any]:
    return {
        "id": "depth",
        "title": "Profundidad (1 = lo he tocado, 5 = lo domino)",
        "kind": "scale",
        "scale_min": 1,
        "scale_max": 5,
    }


def _sources_section() -> dict[str, Any]:
    return {
        "id": "sources",
        "title": "Fuentes de aprendizaje",
        "kind": "open",
        "placeholder": "Docs oficiales, cursos, papers, vídeos, mentores…",
    }


def _notes_section() -> dict[str, Any]:
    return {
        "id": "notes",
        "title": "Notas libres",
        "kind": "open",
        "placeholder": "Lo que más te enganchó, lo que te falta, dudas…",
    }


DOMAIN_TEMPLATES: dict[str, dict[str, Any]] = {
    "ecommerce": {
        "title": "Cuéntame de tu ecommerce",
        "intro": "Quiero entender qué stack y módulos has tocado, para no perderlo.",
        "sections": [
            {
                "id": "stack",
                "title": "Stack frontend",
                "kind": "multi_chips",
                "options": ["React", "Next.js", "Vue", "Nuxt", "Svelte", "Astro", "Remix", "Vanilla"],
                "defaultOpen": True,
            },
            {
                "id": "modules",
                "title": "Módulos que has implementado",
                "kind": "multi_chips",
                "options": [
                    "Pagos",
                    "Carrito",
                    "Checkout",
                    "Fulfillment",
                    "Inventario",
                    "SEO",
                    "Analytics",
                    "Seguridad",
                    "Multi-idioma",
                    "Multi-tienda",
                    "Cupones / promos",
                    "Suscripciones",
                ],
            },
            {
                "id": "payments",
                "title": "Pasarelas de pago",
                "kind": "multi_chips",
                "options": ["Stripe", "PayPal", "Klarna", "Redsys", "Adyen", "Square", "Mercado Pago"],
            },
            _depth_section(),
            _sources_section(),
            _notes_section(),
        ],
    },
    "ai_ml": {
        "title": "Cuéntame de tu trabajo con IA / ML",
        "intro": "Quiero pillar qué áreas y modelos has tocado.",
        "sections": [
            {
                "id": "stack",
                "title": "Stack",
                "kind": "multi_chips",
                "options": [
                    "Python",
                    "PyTorch",
                    "JAX",
                    "TensorFlow",
                    "scikit-learn",
                    "LangChain",
                    "LlamaIndex",
                    "Agno",
                    "Hugging Face",
                    "vLLM",
                ],
                "defaultOpen": True,
            },
            {
                "id": "areas",
                "title": "Áreas",
                "kind": "multi_chips",
                "options": [
                    "LLMs",
                    "Vision",
                    "RAG",
                    "Fine-tuning",
                    "Agents",
                    "RL",
                    "Embeddings",
                    "Speech",
                    "Series temporales",
                    "Recommenders",
                ],
            },
            {
                "id": "models",
                "title": "Modelos tocados",
                "kind": "multi_chips",
                "options": [
                    "GPT-4 / GPT-5",
                    "Claude (Sonnet / Opus / Haiku)",
                    "Gemini",
                    "Llama 3 / 4",
                    "Mistral",
                    "Qwen",
                    "DeepSeek",
                    "Whisper",
                    "Stable Diffusion / Flux",
                ],
            },
            _depth_section(),
            _sources_section(),
            _notes_section(),
        ],
    },
    "mobile": {
        "title": "Cuéntame de tu mobile",
        "intro": "Quiero saber qué plataforma y framework usas.",
        "sections": [
            {
                "id": "platform",
                "title": "Plataforma",
                "kind": "multi_chips",
                "options": ["iOS", "Android", "ambas"],
                "defaultOpen": True,
            },
            {
                "id": "framework",
                "title": "Framework",
                "kind": "multi_chips",
                "options": ["Swift / SwiftUI", "Kotlin / Compose", "React Native", "Flutter", "Expo", "Capacitor"],
            },
            {
                "id": "services",
                "title": "Servicios cloud / backend",
                "kind": "multi_chips",
                "options": ["Firebase", "Supabase", "AWS Amplify", "AppSync", "RevenueCat", "OneSignal"],
            },
            {
                "id": "published",
                "title": "¿Has publicado en stores?",
                "kind": "single_chips",
                "options": ["App Store", "Google Play", "Ambas", "Aún no"],
            },
            _depth_section(),
            _notes_section(),
        ],
    },
    "devops": {
        "title": "Cuéntame de tu trabajo DevOps / infra",
        "intro": "Lo que has tocado, no lo que has visto pasar.",
        "sections": [
            {
                "id": "cloud",
                "title": "Cloud",
                "kind": "multi_chips",
                "options": ["AWS", "GCP", "Azure", "Hetzner", "DigitalOcean", "Fly.io", "Railway", "Cloudflare"],
                "defaultOpen": True,
            },
            {
                "id": "iac",
                "title": "Infraestructura como código",
                "kind": "multi_chips",
                "options": ["Terraform", "Pulumi", "AWS CDK", "Ansible", "CloudFormation", "OpenTofu"],
            },
            {
                "id": "containers",
                "title": "Contenedores / orquestación",
                "kind": "multi_chips",
                "options": ["Docker", "Kubernetes", "Nomad", "ECS", "Cloud Run", "Fly Machines"],
            },
            {
                "id": "cicd",
                "title": "CI / CD",
                "kind": "multi_chips",
                "options": ["GitHub Actions", "GitLab CI", "CircleCI", "ArgoCD", "Flux", "Jenkins"],
            },
            {
                "id": "observability",
                "title": "Observabilidad",
                "kind": "multi_chips",
                "options": ["Prometheus", "Grafana", "Datadog", "Sentry", "OpenTelemetry", "Loki", "ELK"],
            },
            _depth_section(),
            _notes_section(),
        ],
    },
    "cybersec": {
        "title": "Cuéntame de tu trabajo en seguridad",
        "intro": "Vector de seguridad + herramientas.",
        "sections": [
            {
                "id": "areas",
                "title": "Áreas",
                "kind": "multi_chips",
                "options": ["AppSec", "OffSec / Red team", "Blue team", "Cloud security", "Pentest", "DFIR", "GRC"],
                "defaultOpen": True,
            },
            {
                "id": "tools",
                "title": "Herramientas",
                "kind": "multi_chips",
                "options": [
                    "Burp Suite",
                    "Metasploit",
                    "Nmap",
                    "OWASP ZAP",
                    "Wireshark",
                    "SQLMap",
                    "Wazuh",
                    "Cobalt Strike",
                    "Snyk",
                ],
            },
            {
                "id": "certs",
                "title": "Certificaciones / objetivos",
                "kind": "chip_input",
                "placeholder": "OSCP, CEH, CISSP, CRTP…",
            },
            _depth_section(),
            _notes_section(),
        ],
    },
    "design_systems": {
        "title": "Cuéntame de tu trabajo con design systems",
        "intro": "Tooling, componentes y accesibilidad.",
        "sections": [
            {
                "id": "tools",
                "title": "Herramientas de diseño",
                "kind": "multi_chips",
                "options": ["Figma", "Penpot", "Sketch", "Framer", "Adobe XD"],
                "defaultOpen": True,
            },
            {
                "id": "frameworks",
                "title": "Frameworks frontend",
                "kind": "multi_chips",
                "options": ["React", "Vue", "Svelte", "Web Components", "Tailwind", "Radix UI", "shadcn/ui", "Headless UI"],
            },
            {
                "id": "components",
                "title": "Componentes construidos",
                "kind": "chip_input",
                "placeholder": "Buttons, modales, data table, date-picker…",
            },
            {
                "id": "a11y",
                "title": "Accesibilidad WCAG",
                "kind": "single_chips",
                "options": ["Cumplo AA", "Cumplo parcial", "Aún no la he abordado"],
            },
            _depth_section(),
            _notes_section(),
        ],
    },
    "data_eng": {
        "title": "Cuéntame de tu data engineering",
        "intro": "Pipeline + storage + modelado.",
        "sections": [
            {
                "id": "stack",
                "title": "Stack",
                "kind": "multi_chips",
                "options": ["Spark", "Airflow", "Prefect", "Dagster", "dbt", "Polars", "Pandas", "DuckDB"],
                "defaultOpen": True,
            },
            {
                "id": "warehouse",
                "title": "Warehouse / lake",
                "kind": "multi_chips",
                "options": ["Snowflake", "BigQuery", "Redshift", "Databricks", "ClickHouse", "DuckDB local"],
            },
            {
                "id": "streaming",
                "title": "Streaming",
                "kind": "multi_chips",
                "options": ["Kafka", "Pulsar", "Kinesis", "Pub/Sub", "Redpanda", "Flink"],
            },
            {
                "id": "storage",
                "title": "Storage / formats",
                "kind": "multi_chips",
                "options": ["S3 / GCS", "Iceberg", "Delta Lake", "Hudi", "Parquet", "Avro"],
            },
            {
                "id": "modeling",
                "title": "Modelado",
                "kind": "multi_chips",
                "options": ["Kimball / star schema", "Data Vault", "OBT", "Medallion (bronze/silver/gold)"],
            },
            _depth_section(),
            _notes_section(),
        ],
    },
    "web3": {
        "title": "Cuéntame de tu trabajo en web3",
        "intro": "Cadenas, contratos y áreas.",
        "sections": [
            {
                "id": "chains",
                "title": "Cadenas",
                "kind": "multi_chips",
                "options": ["Ethereum", "Solana", "Polygon", "Arbitrum", "Optimism", "Base", "Cosmos", "Bitcoin"],
                "defaultOpen": True,
            },
            {
                "id": "contracts",
                "title": "Smart contracts",
                "kind": "multi_chips",
                "options": ["Solidity", "Vyper", "Rust (Anchor)", "Move", "CosmWasm"],
            },
            {
                "id": "tooling",
                "title": "Tooling",
                "kind": "multi_chips",
                "options": ["Foundry", "Hardhat", "Anchor", "Truffle", "Brownie", "Tenderly"],
            },
            {
                "id": "areas",
                "title": "Áreas",
                "kind": "multi_chips",
                "options": ["DeFi", "NFT / consumer", "DAO / governance", "Infra", "ZK", "Bridges", "Wallets"],
            },
            _depth_section(),
            _notes_section(),
        ],
    },
}


# Aliases — common ways the user might name a domain.
DOMAIN_ALIASES: dict[str, str] = {
    "e-commerce": "ecommerce",
    "comercio electronico": "ecommerce",
    "tienda online": "ecommerce",
    "ai": "ai_ml",
    "ml": "ai_ml",
    "ia": "ai_ml",
    "machine learning": "ai_ml",
    "deep learning": "ai_ml",
    "llm": "ai_ml",
    "llms": "ai_ml",
    "rag": "ai_ml",
    "agentes": "ai_ml",
    "ios": "mobile",
    "android": "mobile",
    "react native": "mobile",
    "flutter": "mobile",
    "infra": "devops",
    "sre": "devops",
    "kubernetes": "devops",
    "k8s": "devops",
    "seguridad": "cybersec",
    "security": "cybersec",
    "pentest": "cybersec",
    "diseno": "design_systems",
    "ux": "design_systems",
    "ui": "design_systems",
    "design": "design_systems",
    "design system": "design_systems",
    "data": "data_eng",
    "etl": "data_eng",
    "data warehouse": "data_eng",
    "blockchain": "web3",
    "smart contracts": "web3",
    "solidity": "web3",
    "defi": "web3",
}


def _canonical(domain: str) -> str:
    norm = domain.strip().lower()
    if norm in DOMAIN_TEMPLATES:
        return norm
    return DOMAIN_ALIASES.get(norm, norm)


def get_template_for(domain: str) -> dict[str, Any] | None:
    """Return the curated template for a domain, or None if not found."""
    key = _canonical(domain)
    return DOMAIN_TEMPLATES.get(key)


def fallback_template(domain: str) -> dict[str, Any]:
    """Generic deep-dive when no curated template matches.

    Uses chip_input (free tags) instead of multi_chips so the specialist can
    pre-fill with whatever the user already mentioned in chat.
    """
    return {
        "title": f"Cuéntame de {domain}",
        "intro": "No tengo una plantilla curada para este dominio, así que vamos en abierto.",
        "sections": [
            {
                "id": "stack",
                "title": "Stack / tecnologías que usas",
                "kind": "chip_input",
                "placeholder": "Añade términos uno a uno…",
                "defaultOpen": True,
            },
            {
                "id": "modules",
                "title": "Subtemas o módulos que has tocado",
                "kind": "chip_input",
                "placeholder": "Lo que has implementado / explorado",
            },
            _depth_section(),
            _sources_section(),
            _notes_section(),
        ],
    }
