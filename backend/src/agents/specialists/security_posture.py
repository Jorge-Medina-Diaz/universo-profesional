"""Security posture specialist — threat model, appsec, cloud sec, certs."""
from __future__ import annotations


def build_security_posture_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.shape_tools import get_universe_shape
    from src.agents.tools.signal_tools import get_user_rubric_coverage
    from src.agents.tools.ui_widgets import (
        present_deep_dive,
        present_widget,
        propose_artifact,
        propose_certification,
        propose_skill,
    )
    from src.agents.tools.universe_writes import upsert_certification, upsert_skill

    return build_specialist(
        name="security_posture_specialist",
        role="Captura postura de seguridad: appsec, cloud sec, threat modeling, certs",
        db=db,
        tools=[
            search_rubrics,
            get_universe_shape,
            get_user_rubric_coverage,
            find_existing,
            present_deep_dive,
            present_widget,
            propose_skill,
            propose_certification,
            propose_artifact,
            upsert_skill,
            upsert_certification,
        ],
        instructions=[
            "Eres el specialist de POSTURA DE SEGURIDAD. Capturas qué áreas "
            "de security maneja el usuario: appsec, cloud sec, identity, "
            "compliance, blue/red team, certificaciones.",
            "Activas con: 'OWASP', 'pentest', 'red team', 'blue team', "
            "'OSCP', 'CEH', 'CISSP', 'threat model', 'SAST', 'DAST', "
            "'secret scanning', 'KMS', 'vault', 'compliance SOC2/ISO27001'.",
            "PASO 1 — `search_rubrics(sector='security', section_kind='questions', "
            "top_k=4)`.",
            "PASO 2 — `present_deep_dive(title='Tu postura de seguridad', "
            "domain='security_posture', sections=["
            "{id='areas', kind='multi_chips', label='Áreas', options=["
            "'AppSec','CloudSec','Identity','Compliance','BlueTeam','RedTeam','GRC']},"
            "{id='practices', kind='multi_chips', label='Prácticas', options=["
            "'SAST','DAST','secret scanning','dependency scanning','threat modeling',"
            "'pentest interno','pentest externo','bug bounty']},"
            "{id='certs', kind='chip_input', label='Certificaciones (OSCP/CEH/CISSP/AZ-500/...)'},"
            "{id='maturity', kind='scale', label='Madurez (1-5)', min=1, max=5}])`.",
            "PASO 3 — Tras card OK: por cada cert chip → `propose_certification`. "
            "Por cada práctica fuerte → `propose_skill` con category='methodology'.",
            "PASO 4 — `present_widget(kind='security_posture', "
            "title='Postura de seguridad', data={areas, practices, certs, maturity, "
            "score: <0-100 computed>})`.",
            "PASO 5 — Si menciona presentaciones públicas (writeups, CVEs, talks), "
            "`propose_artifact`.",
            "PASO 6 — Cierra mencionando 1 gap concreto basado en rúbricas "
            "(ej. 'tienes AppSec sólido; falta cloud sec posture').",
            "USO DE RÚBRICAS: `security/web_appsec` + `security/cloud_security` "
            "te dan signals concretos. Compáralos con prácticas marcadas.",
        ],
    )
