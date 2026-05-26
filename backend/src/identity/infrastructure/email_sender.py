"""Email sender adapters.

`MockEmailSender` ships email to a local SMTP (Mailhog in dev) so the
verification link is visible at http://localhost:8025 — zero credentials
needed.

`BrevoEmailSender` is the production path. Set `EMAIL_PROVIDER=brevo` +
`BREVO_API_KEY` to switch.

The `get_email_sender()` factory picks the right one based on settings.
Callers never instantiate concrete senders directly.
"""
from __future__ import annotations

from email.mime.text import MIMEText
from functools import lru_cache

import aiosmtplib
import structlog

from src.identity.application.ports import EmailSender, EmailSendError
from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


# Legacy short-template subjects — kept around for `send_verification` /
# `send_password_reset` callers that still go through them. New code should
# call `render_template` (email_templates.py) and `send()` directly.
_TEMPLATES_ES = {
    "verify": (
        "Confirma tu email — Universo Profesional",
        "Hola,\n\nConfirma tu cuenta haciendo click aquí:\n{link}\n\n"
        "El enlace expira en 24 horas.\n\n— Universo Profesional",
    ),
    "reset": (
        "Recupera tu contraseña — Universo Profesional",
        "Hola,\n\nUsa este enlace para restablecer tu contraseña (válido 15 minutos):\n{link}\n\n"
        "Si no fuiste tú, ignora este mensaje.\n\n— Universo Profesional",
    ),
}

_TEMPLATES_EN = {
    "verify": (
        "Verify your email — Universo Profesional",
        "Hi,\n\nVerify your account by clicking here:\n{link}\n\n"
        "This link expires in 24 hours.\n\n— Universo Profesional",
    ),
    "reset": (
        "Reset your password — Universo Profesional",
        "Hi,\n\nUse this link to reset your password (valid 15 minutes):\n{link}\n\n"
        "If this wasn't you, ignore this message.\n\n— Universo Profesional",
    ),
}


class _BaseEmailSender:
    """Implements the legacy verify/reset helpers on top of `send`."""

    async def send(  # type: ignore[no-untyped-def]
        self, *, to, subject, body_text, body_html=None, tags=None
    ) -> None:
        raise NotImplementedError

    async def send_verification(self, *, to: str, link: str, locale: str) -> None:
        tmpl = _TEMPLATES_ES if locale.startswith("es") else _TEMPLATES_EN
        subject, body = tmpl["verify"]
        await self.send(
            to=to,
            subject=subject,
            body_text=body.format(link=link),
            tags=["verify"],
        )

    async def send_password_reset(self, *, to: str, link: str, locale: str) -> None:
        tmpl = _TEMPLATES_ES if locale.startswith("es") else _TEMPLATES_EN
        subject, body = tmpl["reset"]
        await self.send(
            to=to,
            subject=subject,
            body_text=body.format(link=link),
            tags=["password_reset"],
        )


class MockEmailSender(_BaseEmailSender, EmailSender):
    """SMTP sender pointing at Mailhog (or any test SMTP) — for dev / tests."""

    async def send(
        self,
        *,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        settings = get_settings()
        if body_html:
            from email.mime.multipart import MIMEMultipart

            msg: MIMEText | MIMEMultipart = MIMEMultipart("alternative")
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            msg = MIMEText(body_text, "plain", "utf-8")
        msg["Subject"] = subject
        from_header = (
            f"{settings.email_from_name} <{settings.email_from}>"
            if settings.email_from_name
            else settings.email_from
        )
        msg["From"] = from_header
        msg["To"] = to
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.email_host,
                port=settings.email_port,
                timeout=10,
            )
            logger.info("email_sent_mock", to=to, subject=subject, tags=tags)
        except Exception as exc:
            logger.warning("email_send_failed", to=to, error=str(exc))
            # We don't raise in dev — Mailhog being down shouldn't break
            # the local register flow (the verification link is still in
            # the API response).


class BrevoEmailSender(_BaseEmailSender, EmailSender):
    """Brevo transactional email via REST.

    Endpoint: POST https://api.brevo.com/v3/smtp/email
    Docs: https://developers.brevo.com/reference/sendtransacemail
    """

    _ENDPOINT = "https://api.brevo.com/v3/smtp/email"

    async def send(
        self,
        *,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        import httpx

        settings = get_settings()
        api_key = settings.brevo_api_key
        if not api_key:
            raise EmailSendError("BREVO_API_KEY not configured")

        payload: dict[str, object] = {
            "sender": {
                "email": settings.email_from,
                "name": settings.email_from_name or "Universo Profesional",
            },
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body_text,
        }
        if body_html:
            payload["htmlContent"] = body_html
        if tags:
            payload["tags"] = tags

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    self._ENDPOINT,
                    headers={
                        "api-key": api_key,
                        "accept": "application/json",
                        "content-type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise EmailSendError(f"Brevo network error: {exc}") from exc

        if resp.status_code >= 500:
            raise EmailSendError(f"Brevo 5xx ({resp.status_code}): {resp.text[:200]}")
        if resp.status_code >= 400:
            # 4xx is permanent — don't retry. Log and raise.
            logger.warning(
                "email_brevo_4xx",
                status=resp.status_code,
                body=resp.text[:200],
                to=to,
            )
            raise EmailSendError(
                f"Brevo {resp.status_code}: {resp.text[:200]}"
            )
        logger.info("email_sent_brevo", to=to, subject=subject, tags=tags)


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    """Pick the configured email provider. Cached singleton."""
    settings = get_settings()
    if settings.email_provider == "brevo":
        if not settings.brevo_api_key:
            logger.warning("brevo_no_key_fallback_mock")
            return MockEmailSender()
        return BrevoEmailSender()
    # Postmark could go here when we add it. For now: mock is the default.
    return MockEmailSender()
