"""Email sender adapters.

`MockEmailSender` writes to stdout AND ships to Mailhog via SMTP, so the
verification email is visible at http://localhost:8025 during local dev.
"""
from __future__ import annotations

from email.mime.text import MIMEText

import aiosmtplib
import structlog

from src.identity.application.ports import EmailSender
from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


_TEMPLATES_ES = {
    "verify": (
        "Confirma tu email — Universo Profesional",
        "Hola,\n\nConfirma tu cuenta haciendo click aquí:\n{link}\n\nEl enlace expira en 24 horas.\n\n— Universo Profesional",
    ),
    "reset": (
        "Recupera tu contraseña — Universo Profesional",
        "Hola,\n\nUsa este enlace para restablecer tu contraseña (válido 15 minutos):\n{link}\n\nSi no fuiste tú, ignora este mensaje.\n\n— Universo Profesional",
    ),
}

_TEMPLATES_EN = {
    "verify": (
        "Verify your email — Universo Profesional",
        "Hi,\n\nVerify your account by clicking here:\n{link}\n\nThis link expires in 24 hours.\n\n— Universo Profesional",
    ),
    "reset": (
        "Reset your password — Universo Profesional",
        "Hi,\n\nUse this link to reset your password (valid 15 minutes):\n{link}\n\nIf this wasn't you, ignore this message.\n\n— Universo Profesional",
    ),
}


class MockEmailSender(EmailSender):
    async def send_verification(self, *, to: str, link: str, locale: str) -> None:
        tmpl = _TEMPLATES_ES if locale.startswith("es") else _TEMPLATES_EN
        subject, body = tmpl["verify"]
        await self._send(to=to, subject=subject, body=body.format(link=link))

    async def send_password_reset(self, *, to: str, link: str, locale: str) -> None:
        tmpl = _TEMPLATES_ES if locale.startswith("es") else _TEMPLATES_EN
        subject, body = tmpl["reset"]
        await self._send(to=to, subject=subject, body=body.format(link=link))

    async def _send(self, *, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.email_host,
                port=settings.email_port,
                timeout=10,
            )
            logger.info("email_sent", to=to, subject=subject)
        except Exception as exc:  # noqa: BLE001
            logger.warning("email_send_failed", to=to, error=str(exc))
            # Fall through silently — tests can inspect the verification link directly
