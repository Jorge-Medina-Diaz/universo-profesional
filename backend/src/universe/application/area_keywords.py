"""Canonical software-area keyword maps + classifier.

This is the single source of truth for area detection. Used by
`shape_service` (foundation) and by the legacy `detect_software_area`
tool (now a thin wrapper).
"""
from __future__ import annotations

from collections.abc import Iterable

# Canonical areas. Mirrors entities.CANONICAL_AREAS.
SOFTWARE_AREA_KEYWORDS: dict[str, list[str]] = {
    "backend": [
        "python",
        "fastapi",
        "django",
        "flask",
        "node",
        "express",
        "nestjs",
        "go",
        "golang",
        "rust",
        "java",
        "spring",
        "kotlin",
        "c#",
        ".net",
        "ruby",
        "rails",
        "elixir",
        "phoenix",
        "postgresql",
        "postgres",
        "mysql",
        "redis",
        "kafka",
        "rabbitmq",
        "grpc",
        "rest api",
        "graphql",
        "microservices",
        "event-driven",
    ],
    "frontend": [
        "react",
        "vue",
        "svelte",
        "angular",
        "tailwind",
        "css",
        "html",
        "typescript",
        "javascript",
        "figma",
        "design system",
        "ui",
        "ux",
        "next.js",
        "nextjs",
        "remix",
        "nuxt",
        "vite",
        "webpack",
        "rsc",
        "a11y",
    ],
    "devops": [
        "kubernetes",
        "k8s",
        "docker",
        "terraform",
        "ansible",
        "pulumi",
        "cicd",
        "ci/cd",
        "github actions",
        "gitlab",
        "argocd",
        "argo cd",
        "prometheus",
        "grafana",
        "datadog",
        "sre",
        "devops",
        "helm",
        "linkerd",
        "istio",
        "service mesh",
    ],
    "cloud": [
        "aws",
        "gcp",
        "azure",
        "lambda",
        "ec2",
        "s3",
        "rds",
        "ecs",
        "eks",
        "gke",
        "aks",
        "cloudwatch",
        "cloudfront",
        "iam",
        "vpc",
        "route53",
        "dynamodb",
        "fargate",
        "cloud run",
        "app engine",
        "azure functions",
    ],
    "platform": [
        "backstage",
        "internal developer platform",
        "idp",
        "developer experience",
        "dx",
        "golden path",
        "self-service",
        "platform engineering",
    ],
    "mobile": [
        "swift",
        "swiftui",
        "android",
        "ios",
        "react native",
        "flutter",
        "expo",
        "jetpack compose",
    ],
    "ai_ml": [
        "pytorch",
        "tensorflow",
        "jax",
        "scikit-learn",
        "sklearn",
        "ml",
        "machine learning",
        "deep learning",
        "hugging face",
        "transformers",
        "computer vision",
        "nlp",
        "fine-tuning",
        "fine tuning",
        "embedding",
        "model serving",
        "vllm",
        "ollama",
    ],
    "llm_agents": [
        "langchain",
        "llamaindex",
        "rag",
        "llm",
        "agno",
        "crewai",
        "langgraph",
        "autogen",
        "multi-agent",
        "agentic",
        "agent",
        "tool calling",
        "tool use",
        "mcp",
        "a2a",
        "react agent",
        "reflexion",
        "langsmith",
        "langfuse",
        "phoenix",
    ],
    "data_eng": [
        "spark",
        "airflow",
        "dbt",
        "prefect",
        "dagster",
        "snowflake",
        "bigquery",
        "redshift",
        "databricks",
        "iceberg",
        "delta lake",
        "data pipeline",
        "etl",
        "elt",
        "lakehouse",
        "data warehouse",
        "data lake",
        "kafka streams",
    ],
    "security": [
        "burp",
        "metasploit",
        "nmap",
        "owasp",
        "appsec",
        "pentest",
        "ciso",
        "blue team",
        "red team",
        "soc",
        "wazuh",
        "snyk",
        "threat model",
        "vault",
        "secrets management",
        "kms",
    ],
}


# Areas where backend and frontend overlap → reported as fullstack.
FRONT_BACK_PAIR = {"frontend", "backend"}


def collect_text_blob(parts: Iterable[str]) -> str:
    """Join arbitrary text parts into a single lowercased blob."""
    return " ".join(str(p) for p in parts if p).lower()


def score_areas(blob: str) -> dict[str, int]:
    """Return {area: keyword_hits} for each area with >= 1 hit."""
    scores: dict[str, int] = {}
    for area, kws in SOFTWARE_AREA_KEYWORDS.items():
        hits = 0
        for kw in kws:
            if kw in blob:
                hits += 1
        if hits:
            scores[area] = hits
    return scores


def area_hits_per_kw(blob: str, area: str) -> int:
    """For a single area, count how many of its keywords appear in blob."""
    kws = SOFTWARE_AREA_KEYWORDS.get(area, [])
    return sum(1 for kw in kws if kw in blob)
