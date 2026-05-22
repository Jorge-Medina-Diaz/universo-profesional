"""Cloud posture specialist — captures AWS / GCP / Azure + IaC + platform engineering work.

Distinct from `skill_specialist` (which would capture "AWS" as one of many
skills): this one captures the SHAPE of the user's cloud posture across
providers — depth on AWS vs GCP vs Azure, IaC tool, observability stack,
cost discipline, platform team practices.
"""
from __future__ import annotations


def build_cloud_posture_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.shape_tools import get_universe_shape
    from src.agents.tools.signal_tools import get_user_rubric_coverage
    from src.agents.tools.ui_widgets import (
        present_deep_dive,
        present_widget,
        propose_artifact,
        propose_skill_batch,
    )
    from src.agents.tools.universe_writes import upsert_project, upsert_skill

    return build_specialist(
        name="cloud_posture_specialist",
        role="Captura postura cloud (AWS/GCP/Azure + IaC + Platform Eng) del usuario",
        db=db,
        tools=[
            search_rubrics,
            get_universe_shape,
            get_user_rubric_coverage,
            find_existing,
            present_deep_dive,
            present_widget,
            propose_skill_batch,
            propose_artifact,
            upsert_project,
            upsert_skill,
        ],
        instructions=[
            "Eres el specialist de POSTURA CLOUD. Capturas qué proveedores "
            "domina, qué servicios usa, qué IaC, qué stack de observabilidad y "
            "qué nivel de madurez platform-eng tiene.",
            "Activas con: 'uso AWS', 'monté en GCP', 'migrar a Azure', "
            "'K8s en prod', 'Terraform', 'Pulumi', 'Helm', 'IaC', 'IDP', "
            "'platform team', 'DX', 'Backstage', 'golden paths', "
            "'self-service infra', 'developer experience'.",
            "PASO 1 — `search_rubrics(query=<user_text>, sector='cloud', "
            "section_kind='questions', top_k=4)` + segunda call con "
            "sector='platform' si menciona DX/IDP/golden paths.",
            "PASO 2 — `present_deep_dive(title='Tu postura cloud', "
            "domain='cloud_stack', sections=["
            "{id='providers', kind='multi_chips', label='Proveedores', "
            "options=['AWS','GCP','Azure','DO','OnPrem']},"
            "{id='services_used', kind='chip_input', label='Servicios principales'},"
            "{id='iac_tool', kind='single_chips', label='IaC', "
            "options=['Terraform','Pulumi','CDK','Crossplane','Bicep','None']},"
            "{id='observability', kind='multi_chips', label='Observabilidad', "
            "options=['CloudWatch','Datadog','Grafana','Prometheus','New Relic','Sentry']},"
            "{id='cost_model', kind='single_chips', label='Madurez de coste', "
            "options=['ad-hoc','tagging+reports','FinOps básico','FinOps avanzado']},"
            "{id='platform_maturity', kind='scale', label='Madurez platform-eng (1-5)', min=1, max=5}])`.",
            "PASO 3 — Cuando el card vuelva con payload válido: por cada "
            "servicio chip_input emite `propose_skill_batch` con category='tool' "
            "(ej. Lambda, RDS, Terraform, Helm). El coherence engine hará merge "
            "con skills 'AWS' existentes vía semantic_matcher.",
            "PASO 4 — `present_widget(kind='cloud_coverage', title='Cobertura "
            "cloud', data={providers: [...], services_by_provider: {...}, "
            "iac_tool, observability_stack, cost_model, platform_maturity})`.",
            "PASO 5 — Si user mencionó un repo público con IaC (terraform-aws-..., "
            "pulumi-azure-...), llama `propose_artifact(type='github_repo', ...)`.",
            "PASO 6 — Cierra con 1-2 frases concretas: '<provider> con "
            "<iac_tool> capturado. Si tu primary_area pasa a ser cloud te lo "
            "noto en el tech_radar próximo turno'.",
            "USO DE RÚBRICAS: las rúbricas `cloud/aws_services`, "
            "`cloud/gcp_services`, `cloud/azure_services`, "
            "`platform_eng/developer_experience`, "
            "`platform_eng/platform_abstraction` te dan signals de seniority. "
            "Compáralos con los chips que el usuario marcó y nombra 1 gap "
            "concreto si destaca (ej. 'usas IAM users en lugar de SSO/AssumeRole "
            "— es señal de junior; podemos arreglarlo').",
            "NO eres skill_specialist puro: si el usuario suelta 1 sola skill "
            "('uso Terraform'), prefieres ruta a skill. Aquí capturas el SISTEMA "
            "cloud completo.",
        ],
    )
