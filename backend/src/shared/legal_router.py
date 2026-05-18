"""Static legal pages (placeholders requiring review by counsel)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/legal/terms", response_class=HTMLResponse)
async def terms() -> HTMLResponse:
    return HTMLResponse(_render(
        "Términos y Condiciones",
        """
        <p><em>(Borrador — pendiente revisión legal.)</em></p>
        <p>Estos Términos rigen el uso del servicio Universo Profesional…</p>
        """,
    ))


@router.get("/legal/privacy", response_class=HTMLResponse)
async def privacy() -> HTMLResponse:
    return HTMLResponse(_render(
        "Política de Privacidad",
        """
        <p><em>(Borrador — pendiente revisión legal.)</em></p>
        <p>Responsable: jorge@webtools.es. Base legal: consentimiento (Art. 6.1.a) +
        ejecución de contrato (Art. 6.1.b). Hosting UE. Retención: 30 días tras borrado.</p>
        <p>Tus derechos (ARCO-POL): acceso, rectificación, supresión, oposición,
        portabilidad y limitación. Puedes ejercerlos desde <a href="/settings">Ajustes</a>.</p>
        """,
    ))


@router.get("/legal/cookies", response_class=HTMLResponse)
async def cookies() -> HTMLResponse:
    return HTMLResponse(_render(
        "Política de Cookies",
        """
        <p><em>(Borrador — pendiente revisión legal.)</em></p>
        <p>Esenciales: token de sesión. Analytics: opt-in. Marketing: opt-in.</p>
        """,
    ))


def _render(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>{title}</title><style>body{{font-family:system-ui;max-width:680px;margin:3rem auto;padding:0 1rem;color:#1f1f1f}}h1{{font-size:1.5rem}}a{{color:#1d4ed8}}</style></head>
<body><h1>{title}</h1>{body}</body></html>"""
