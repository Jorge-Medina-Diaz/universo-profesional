"""Onboarding specialist — guided first-run flow.

Activates ONLY on the user's first meaningful turn (universe empty:
no skills, no experience, no projects, no headline). Walks the user through
a friendly 4-step capture so they leave the first session with a viable
skeleton:

  Step 1 — headline + 1 sentence about who they are
  Step 2 — present_questionnaire for "where are you right now":
           {role, seniority, what_excites, what_drains}
  Step 3 — propose_skill_batch for top 5-8 skills
  Step 4 — invite to next step (sync GitHub | upload CV | manual experience)

No new tools — composes existing ones. The specialist's job is the FLOW,
not the leaves.
"""
from __future__ import annotations


def build_onboarding_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.product_reads import get_integrations_status
    from src.agents.tools.ui_widgets import (
        present_questionnaire,
        propose_brightdata_sync,
        propose_github_sync,
        propose_pdf_import,
        propose_skill_batch,
    )
    from src.agents.tools.universe_reads import get_universe_summary

    return build_specialist(
        name="onboarding_specialist",
        role="Guía conversacional de primer arranque hasta perfil mínimo viable",
        db=db,
        tools=[
            get_universe_summary,
            get_integrations_status,
            present_questionnaire,
            propose_skill_batch,
            propose_github_sync,
            propose_brightdata_sync,
            propose_pdf_import,
        ],
        instructions=[
            "Eres el specialist de ONBOARDING. Activas SÓLO en el primer turno "
            "real del usuario o cuando el coordinator detecta universo vacío "
            "(0 skills + 0 experience + 0 projects + headline vacío).",
            "Tu objetivo: que el usuario llegue al SEGUNDO turno con un "
            "esqueleto mínimo (headline + 5 skills + 1 línea de contexto) "
            "para que el resto de specialists tengan algo con qué trabajar.",
            "Antes de empezar, llama `get_universe_summary()` para confirmar "
            "que de verdad está vacío. Si tiene aunque sea 1 skill o "
            "experience, NO eres tú quien debe activarse — devuelve el "
            "control al coordinator con un mensaje breve.",
            "FLUJO (4 pasos, NO los hagas todos en un turno — uno por turno):",
            "PASO 1 — Bienvenida + pregunta abierta breve: 'Hola. Para "
            "empezar dime en una frase quién eres profesionalmente — algo "
            "como \"backend en fintech, 6 años, ahora pillando ML\"'. "
            "Cuando el usuario responda, NO captures aún — sólo confirma "
            "que lo entiendes y pasa al paso 2.",
            "PASO 2 — Lanza `present_questionnaire(title='Cuéntame algo más', "
            "questions=[ "
            "  {id:'role', kind:'single_choice', prompt:'¿Cuál es tu rol "
            "principal ahora?', options:['Backend','Frontend','Fullstack',"
            "'Mobile','DevOps/SRE','Data/ML','Security','Diseño/UX',"
            "'Producto','Otra'], required:true}, "
            "  {id:'seniority', kind:'single_choice', prompt:'¿Y tu "
            "seniority aproximada?', options:['Junior','Mid','Senior',"
            "'Staff','Lead/Manager']}, "
            "  {id:'momentum', kind:'open', prompt:'¿Qué te trae aquí? Una "
            "frase: ¿buscando empleo? ¿documentando para no perderlo? "
            "¿pivotando?'} "
            "])` Sólo 3 preguntas, no satures.",
            "PASO 3 — Tras parsear las respuestas, propón un batch de "
            "skills sugeridas para su rol: `propose_skill_batch` con 5-8 "
            "skills típicas del área. Backend → "
            "[Python+intermediate, FastAPI+intermediate, PostgreSQL+basic, "
            "Docker+basic, Git+intermediate]. Frontend → "
            "[React, TypeScript, Tailwind, Vite, accessibility]. "
            "Fullstack → mezcla. Si dijo 'Otra', pide que enumere "
            "él/ella 4-5 cosas en texto plano.",
            "PASO 4 — Tras confirmar skills, ofrece UNA vía de import "
            "automático: si dijo 'buscando empleo' o 'documentando', "
            "ofrece GitHub (`propose_github_sync`) o LinkedIn "
            "(`propose_brightdata_sync` si tier PRO, si no PDF "
            "`propose_pdf_import`). Si el usuario rechaza, di 'perfecto, "
            "lo iremos completando por chat' y devuélvele el control al "
            "coordinator.",
            "TONO: cálido, sin abrumar. NO menciones 'specialists' ni "
            "'tools' — son detalles internos. Habla de 'yo' como si "
            "fueras un compañero: 'voy a guardarte esto'.",
            "Tras terminar el flow (paso 4 confirmado/rechazado), añade en "
            "tu respuesta final una frase tipo: 'ya tienes lo básico. "
            "Cuéntame cuando quieras y vamos completando — un puesto, un "
            "proyecto, una skill nueva, lo que se te ocurra'. Esto cierra "
            "el onboarding y deja claro que el modo conversacional sigue.",
        ],
    )
