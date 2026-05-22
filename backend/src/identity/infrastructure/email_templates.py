"""Email template renderer — produces `{subject, text, html}` per template.

Templates are inline Jinja-lite strings keyed by `(name, locale)`. Kept in
this file (not as separate .html files) so the dep graph is tight and the
production image doesn't need a templates directory mounted.

For now we ship a clean table-based HTML layout for each transactional
flavour. Gmail / Outlook / Apple Mail all handle the basics fine. When we
grow we'll move to MJML or react-email, but this avoids the build-time
preprocessing dep.
"""
from __future__ import annotations

from string import Template
from typing import Any


def _safe_get(ctx: dict[str, Any], key: str, default: str = "") -> str:
    v = ctx.get(key)
    return "" if v is None else str(v)


# --- Layout shared across all templates ----------------------------------

_LAYOUT = Template(
    """<!doctype html>
<html lang="${locale}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>${subject}</title>
</head>
<body style="margin:0;padding:0;background:#f8f5ed;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0a0a0a;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f8f5ed;padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background:#ffffff;border-radius:24px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <tr><td style="padding-bottom:24px;">
          <div style="display:inline-block;width:36px;height:36px;border-radius:50%;background:#6ece9d;line-height:36px;text-align:center;color:#0a0a0a;font-weight:700;font-size:18px;">U</div>
          <span style="margin-left:10px;font-size:16px;font-weight:600;color:#0a0a0a;">Universo Profesional</span>
        </td></tr>
        <tr><td>${body_html}</td></tr>
        <tr><td style="padding-top:32px;border-top:1px solid rgba(0,0,0,0.06);font-size:12px;color:#707070;line-height:1.6;">
          ${footer}
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
)


_FOOTER_ES = (
    "Recibes este email porque tienes una cuenta en Universo Profesional. "
    "Para gestionar tus preferencias visita "
    '<a href="${frontend_base_url}/settings" style="color:#0a0a0a;">tu configuración</a>.'
)
_FOOTER_EN = (
    "You're receiving this because you have a Universo Profesional account. "
    'Manage your preferences in <a href="${frontend_base_url}/settings" style="color:#0a0a0a;">settings</a>.'
)


# --- Per-template bodies (subject + text + html) -------------------------


def _welcome(locale: str, ctx: dict[str, Any]) -> dict[str, str]:
    name = _safe_get(ctx, "display_name", "")
    onboarding_url = _safe_get(
        ctx, "onboarding_url", f"{_safe_get(ctx, 'frontend_base_url')}/onboarding"
    )
    if locale == "en":
        subject = "Welcome to Universo Profesional"
        text = (
            f"Hi {name},\n\nWelcome to Universo Profesional. Your account is ready — "
            f"the next step is to import your existing CV or LinkedIn so the agent has "
            f"something to work with.\n\nStart onboarding: {onboarding_url}\n\n"
            f"— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hi {name},</h1>'
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            "Welcome to Universo Profesional. Your account is ready. The next step is "
            "to import your existing CV or LinkedIn so the agent has something to work with."
            "</p>"
            f'<p style="margin:24px 0;"><a href="{onboarding_url}" '
            'style="display:inline-block;background:#ffda6e;color:#0a0a0a;padding:12px 24px;'
            'border-radius:12px;text-decoration:none;font-weight:600;font-size:14px;">'
            "Start onboarding</a></p>"
        )
    else:
        subject = "Bienvenida a Universo Profesional"
        text = (
            f"Hola {name},\n\nBienvenida a Universo Profesional. Tu cuenta ya está lista. "
            f"El siguiente paso es importar tu CV o LinkedIn para que el agente tenga "
            f"con qué trabajar.\n\nEmpieza aquí: {onboarding_url}\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hola {name},</h1>'
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            "Bienvenida a Universo Profesional. Tu cuenta ya está lista. El siguiente paso "
            "es importar tu CV o LinkedIn para que el agente tenga con qué trabajar."
            "</p>"
            f'<p style="margin:24px 0;"><a href="{onboarding_url}" '
            'style="display:inline-block;background:#ffda6e;color:#0a0a0a;padding:12px 24px;'
            'border-radius:12px;text-decoration:none;font-weight:600;font-size:14px;">'
            "Empezar onboarding</a></p>"
        )
    return {"subject": subject, "text": text, "body_html": body_html}


def _payment_received(locale: str, ctx: dict[str, Any]) -> dict[str, str]:
    name = _safe_get(ctx, "display_name", "")
    plan = _safe_get(ctx, "plan", "Premium").capitalize()
    if locale == "en":
        subject = f"Welcome to {plan} — Universo Profesional"
        text = (
            f"Hi {name},\n\nYour {plan} subscription is now active. You can manage it any "
            f"time from Settings → Billing.\n\nThanks for the support.\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hi {name},</h1>'
            f'<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            f"Your <strong>{plan}</strong> subscription is now active. Manage it any time "
            "from Settings → Billing.</p>"
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">Thanks for the support.</p>'
        )
    else:
        subject = f"Bienvenida a {plan} — Universo Profesional"
        text = (
            f"Hola {name},\n\nTu suscripción {plan} ya está activa. Puedes gestionarla "
            f"cuando quieras desde Ajustes → Facturación.\n\nGracias por el apoyo.\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hola {name},</h1>'
            f'<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            f"Tu suscripción <strong>{plan}</strong> ya está activa. Puedes gestionarla "
            "cuando quieras desde Ajustes → Facturación.</p>"
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">Gracias por el apoyo.</p>'
        )
    return {"subject": subject, "text": text, "body_html": body_html}


def _subscription_canceled(locale: str, ctx: dict[str, Any]) -> dict[str, str]:
    name = _safe_get(ctx, "display_name", "")
    if locale == "en":
        subject = "Subscription canceled — Universo Profesional"
        text = (
            f"Hi {name},\n\nWe've cancelled your paid subscription. You'll keep access "
            f"until the end of the current billing cycle, then your account drops to free.\n\n"
            f"You can resubscribe any time.\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hi {name},</h1>'
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            "We've cancelled your paid subscription. You'll keep access until the end "
            "of the current billing cycle, then your account drops to free.</p>"
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">You can resubscribe any time.</p>'
        )
    else:
        subject = "Suscripción cancelada — Universo Profesional"
        text = (
            f"Hola {name},\n\nHemos cancelado tu suscripción de pago. Mantienes acceso "
            f"hasta el final del ciclo actual, después tu cuenta vuelve a free.\n\n"
            f"Puedes resuscribirte cuando quieras.\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hola {name},</h1>'
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            "Hemos cancelado tu suscripción de pago. Mantienes acceso hasta el final del "
            "ciclo actual, después tu cuenta vuelve a free.</p>"
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">Puedes resuscribirte cuando quieras.</p>'
        )
    return {"subject": subject, "text": text, "body_html": body_html}


def _account_deleted(locale: str, ctx: dict[str, Any]) -> dict[str, str]:
    name = _safe_get(ctx, "display_name", "")
    if locale == "en":
        subject = "Account deleted — Universo Profesional"
        text = (
            f"Hi {name},\n\nWe've received your account deletion request. Your data has "
            f"been removed; we'll purge backups within 30 days.\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hi {name},</h1>'
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            "We've received your account deletion request. Your data has been removed; "
            "we'll purge backups within 30 days.</p>"
        )
    else:
        subject = "Cuenta eliminada — Universo Profesional"
        text = (
            f"Hola {name},\n\nHemos recibido tu solicitud de eliminación de cuenta. Tus "
            f"datos han sido borrados; los backups se purgarán en 30 días.\n\n— Universo Profesional"
        )
        body_html = (
            f'<h1 style="font-size:22px;margin:0 0 12px;font-weight:600;">Hola {name},</h1>'
            '<p style="margin:0 0 16px;line-height:1.6;font-size:15px;">'
            "Hemos recibido tu solicitud de eliminación de cuenta. Tus datos han sido "
            "borrados; los backups se purgarán en 30 días.</p>"
        )
    return {"subject": subject, "text": text, "body_html": body_html}


_RENDERERS = {
    "welcome": _welcome,
    "payment_received": _payment_received,
    "subscription_canceled": _subscription_canceled,
    "account_deleted": _account_deleted,
}


def render_template(
    name: str, *, locale: str, context: dict[str, Any] | None = None
) -> dict[str, str]:
    """Render a transactional template.

    Returns `{subject, text, html}`. Falls back to the welcome template if
    the name isn't registered (logs a warning rather than crashing — we
    don't want a missing template to break a billing webhook).
    """
    ctx = dict(context or {})
    # Ensure the frontend URL is always available to bodies/footers.
    if "frontend_base_url" not in ctx:
        from src.shared.config import get_settings

        ctx["frontend_base_url"] = get_settings().frontend_base_url

    lang = "en" if locale.startswith("en") else "es"
    renderer = _RENDERERS.get(name)
    if renderer is None:
        import structlog

        structlog.get_logger(__name__).warning("unknown_email_template", name=name)
        renderer = _welcome

    parts = renderer(lang, ctx)
    footer_tmpl = _FOOTER_EN if lang == "en" else _FOOTER_ES
    footer = Template(footer_tmpl).safe_substitute(
        frontend_base_url=ctx.get("frontend_base_url", "")
    )
    html = _LAYOUT.safe_substitute(
        locale=lang,
        subject=parts["subject"],
        body_html=parts["body_html"],
        footer=footer,
    )
    return {"subject": parts["subject"], "text": parts["text"], "html": html}
