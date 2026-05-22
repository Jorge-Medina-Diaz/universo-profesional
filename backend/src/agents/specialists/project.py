"""Project specialist."""
from __future__ import annotations


def build_project_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.shape_tools import upsert_artifact
    from src.agents.tools.ui_widgets import propose_artifact, propose_project
    from src.agents.tools.universe_writes import upsert_project

    return build_specialist(
        name="project_specialist",
        role="Captura proyectos personales, side, OSS o de trabajo",
        db=db,
        tools=[
            propose_project,
            upsert_project,
            find_existing,
            propose_artifact,
            upsert_artifact,
        ],
        instructions=[
            "Eres el specialist de proyectos.",
            "Antes de crear, usa `find_existing(entity_type='project', query=...)` para "
            "detectar proyectos ya conocidos (mismo nombre o similar — el engine fusionará).",
            "Captura: nombre, descripción breve, rol del usuario, tipo (side|oss|entrepreneurship|work), "
            "tech_stack, highlights y impact.",
            "Si el usuario menciona un repo GitHub, sugiere `propose_github_sync` en su lugar.",
            "Llama `propose_project` antes de persistir; luego `upsert_project`.",
            "ARTIFACT: si el proyecto tiene URL pública (repo, demo, post anunciándolo, "
            "talk), tras persistirlo llama `propose_artifact(type=..., title=..., url=..., "
            "linked_project_id=<id del proyecto>)`. Cuando el usuario confirme, "
            "llama `upsert_artifact` con los datos devueltos. Esto convierte el "
            "proyecto en ciudadano de portfolio público.",
        ],
    )
