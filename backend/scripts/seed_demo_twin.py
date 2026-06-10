"""Seed the landing demo twin: a fictional, clearly-labeled profile («Vega Demo»).

Idempotent: if the `demo` slug already resolves, exits 0 (use --force to
re-enable/refresh curation). Drives the REAL product pipeline over HTTP
(register → verify → entities through the coherence path → enable twin), so
embeddings/enrichment/snapshot happen exactly as for a real user; finishes by
enqueuing graph enrichment directly.

Run inside the backend container:
    python -m scripts.seed_demo_twin [--force]
Env: DEMO_BASE_URL (default http://localhost:8000),
     DEMO_MAILHOG_URL (default http://cvs-mailhog:8025).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import sys

import httpx

BASE = os.getenv("DEMO_BASE_URL", "http://localhost:8000")
MAILHOG = os.getenv("DEMO_MAILHOG_URL", "http://cvs-mailhog:8025")
EMAIL = "demo-twin@universo.pro"
PASSWORD = os.getenv("DEMO_TWIN_PASSWORD", "VegaDemo-2026!seed")
SLUG = "demo"

CHARTER = (
    "Eres el twin de «Vega Demo», un perfil FICTICIO de demostración de "
    "Universo Profesional. Si te preguntan si eres real, dilo claramente: "
    "eres una demo. Responde con cercanía sobre la trayectoria ficticia; "
    "nada de salario ni contacto — invita a crear su propio universo."
)

SUGGESTED = [
    "¿Cuál es tu experiencia con Python?",
    "¿Qué proyecto te enorgullece más?",
    "¿Encajarías en un equipo de datos?",
    "¿Qué no sabes hacer?",
]

EXPERIENCES = [
    {
        "role": "Staff Data Engineer",
        "organization": "Northwind Analytics",
        "start_date": "2022-03-01",
        "is_current": True,
        "location": "Madrid (remoto)",
        "description": (
            "Lidero la plataforma de datos: lakehouse sobre Spark y Delta en "
            "AWS, orquestación con Airflow, contratos de datos y un catálogo "
            "interno. Reduje el coste de cómputo un 38% renegociando el "
            "particionado y moviendo cargas a spot."
        ),
        "highlights": [
            "Migré 40+ pipelines de Pentaho a Spark estructurado",
            "Diseñé el data mesh por dominios con contratos versionados",
            "Mentoría a 4 ingenieros junior",
        ],
    },
    {
        "role": "Senior Backend Engineer",
        "organization": "Lumen Health",
        "start_date": "2019-06-01",
        "end_date": "2022-02-28",
        "is_current": False,
        "description": (
            "APIs clínicas FastAPI/PostgreSQL con FHIR, mensajería con Kafka "
            "y observabilidad con Prometheus/Grafana. Certificación ISO 27001 "
            "del equipo: diseñé el control de acceso por roles y la auditoría."
        ),
        "highlights": [
            "Latencia p95 de 800ms a 120ms reescribiendo el agregador FHIR",
            "Implanté trunk-based development y despliegue continuo",
        ],
    },
    {
        "role": "Backend Developer",
        "organization": "Tundra Games",
        "start_date": "2016-09-01",
        "end_date": "2019-05-31",
        "is_current": False,
        "description": (
            "Servicios de juego multijugador en Python y Go: matchmaking, "
            "economía virtual e inventario, sobre Redis y PostgreSQL."
        ),
    },
]

PROJECTS = [
    {
        "name": "Atlas — catálogo de datos open source",
        "description": (
            "Catálogo de datos con linaje automático parseando planes de "
            "Spark; 1.2k estrellas en GitHub. Backend FastAPI + grafo en "
            "PostgreSQL, frontend React."
        ),
        "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL", "Spark"],
        "impact": "Adoptado por 3 empresas medianas para gobierno de datos",
        "is_current": True,
    },
    {
        "name": "Pipeline de ML para detección de fraude",
        "description": (
            "Feature store + entrenamiento continuo (XGBoost) + serving de "
            "baja latencia para detección de fraude en pagos. AUC 0.94 y "
            "-23% de falsos positivos respecto al sistema de reglas."
        ),
        "tech_stack": ["Python", "XGBoost", "Kafka", "Feast"],
    },
    {
        "name": "Charla: «Data contracts en la práctica» (PyConES)",
        "description": "Charla aceptada en PyConES sobre contratos de datos con ejemplos reales de Northwind.",
    },
]

SKILLS = [
    ("Python", "expert", 9),
    ("SQL", "expert", 10),
    ("Apache Spark", "advanced", 5),
    ("PostgreSQL", "advanced", 8),
    ("FastAPI", "advanced", 5),
    ("Kafka", "advanced", 4),
    ("Airflow", "advanced", 4),
    ("AWS", "advanced", 6),
    ("Docker", "advanced", 7),
    ("Kubernetes", "intermediate", 3),
    ("Terraform", "intermediate", 3),
    ("Go", "intermediate", 3),
    ("React", "intermediate", 4),
    ("dbt", "intermediate", 2),
    ("Grafana", "intermediate", 4),
    ("Liderazgo técnico", "advanced", 4),
    ("Mentoría", "advanced", 4),
    ("Comunicación técnica", "advanced", 6),
]

CERTS = [
    {"name": "AWS Solutions Architect Associate", "issuer": "Amazon Web Services", "issued_on": "2023-05-15"},
    {"name": "Databricks Data Engineer Professional", "issuer": "Databricks", "issued_on": "2024-02-10"},
]

LANGS = [
    {"code": "es", "name": "Español", "level": "nativo"},
    {"code": "en", "name": "Inglés", "level": "C1"},
]


async def _verify_via_mailhog(c: httpx.AsyncClient) -> None:
    await asyncio.sleep(1.5)
    msgs = (await c.get(f"{MAILHOG}/api/v2/messages")).json()
    for item in msgs.get("items", []):
        headers = json.dumps(item["Content"]["Headers"].get("To", []))
        if EMAIL.split("@")[0] in headers:
            body = item["Content"]["Body"]
            try:
                body = base64.b64decode(body).decode("utf-8", "replace")
            except Exception:
                pass
            m = re.search(r"token=([A-Za-z0-9._\-]+)", body)
            if m:
                r = await c.post(f"{BASE}/api/v1/auth/verify", json={"token": m.group(1)})
                r.raise_for_status()
                return
    raise RuntimeError("verification email not found in mailhog")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=60) as c:
        existing = await c.get(f"{BASE}/api/v1/public/twin/{SLUG}")
        if existing.status_code == 200 and not args.force:
            print(f"demo twin already live at /#/t/{SLUG} — nothing to do")
            return 0

        r = await c.post(
            f"{BASE}/api/v1/auth/register",
            json={"email": EMAIL, "password": PASSWORD, "display_name": "Vega Demo"},
        )
        if r.status_code in (200, 201):
            print("registered demo user")
            await _verify_via_mailhog(c)
        elif r.status_code in (400, 409, 422):
            print("demo user already exists")
        else:
            r.raise_for_status()

        r = await c.post(f"{BASE}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Seed entities through the real API (coherence + embeddings pipeline).
        created = 0
        for exp in EXPERIENCES:
            rr = await c.post(f"{BASE}/api/v1/universe/experience", json=exp, headers=h)
            created += rr.status_code == 201
        for proj in PROJECTS:
            rr = await c.post(f"{BASE}/api/v1/universe/project", json=proj, headers=h)
            created += rr.status_code == 201
        for name, level, years in SKILLS:
            rr = await c.post(
                f"{BASE}/api/v1/universe/skill",
                json={"name": name, "level": level, "years": years},
                headers=h,
            )
            created += rr.status_code == 201
        for cert in CERTS:
            rr = await c.post(f"{BASE}/api/v1/universe/certification", json=cert, headers=h)
            created += rr.status_code == 201
        for lang in LANGS:
            rr = await c.post(f"{BASE}/api/v1/universe/language", json=lang, headers=h)
            created += rr.status_code == 201
        print(f"entities created this run: {created}")

        r = await c.put(
            f"{BASE}/api/v1/twin",
            json={
                "enabled": True,
                "slug": SLUG,
                "curation": {
                    "visible_kinds": [
                        "experience", "education", "skill", "project",
                        "certification", "language", "achievement",
                    ],
                    "charter": CHARTER,
                    "suggested_questions": SUGGESTED,
                },
            },
            headers=h,
        )
        r.raise_for_status()
        print(f"twin enabled at slug '{r.json()['slug']}'")

        # Derive the user id from any owned row (auth/me path varies).
        probe = await c.post(
            f"{BASE}/api/v1/universe/skill",
            json={"name": "Universo Profesional (demo)", "level": "advanced"},
            headers=h,
        )
        user_id = probe.json().get("user_id") if probe.status_code == 201 else None

    # Kick enrichment (edges/communities) directly — same call imports use.
    if user_id:
        from uuid import UUID

        from src.universe.infrastructure.scheduler import enqueue_graph_enrichment

        ok = await enqueue_graph_enrichment(UUID(str(user_id)))
        print(f"graph enrichment enqueued: {ok}")

    print(f"DONE — try it: /#/t/{SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
