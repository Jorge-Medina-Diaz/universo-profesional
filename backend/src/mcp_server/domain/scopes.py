"""OAuth scope definitions per §I.3 of the spec."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    name: str
    description: str
    destructive: bool = False


SCOPES: dict[str, Scope] = {
    "universe:read": Scope(
        "universe:read", "Leer tu universo profesional (perfil, experiencias, skills…)"
    ),
    "universe:write": Scope(
        "universe:write", "Añadir y modificar entradas en tu universo profesional"
    ),
    "universe:delete": Scope(
        "universe:delete", "Borrar entradas de tu universo profesional", destructive=True
    ),
    "documents:read": Scope("documents:read", "Listar y ver tus documentos generados"),
    "documents:generate": Scope(
        "documents:generate", "Generar CVs y cartas adaptadas a una oferta"
    ),
    "applications:read": Scope("applications:read", "Ver tu tracker de candidaturas"),
    "applications:write": Scope("applications:write", "Crear y actualizar candidaturas"),
    "preferences:read": Scope("preferences:read", "Leer tus preferencias de carrera"),
    "preferences:write": Scope("preferences:write", "Modificar tus preferencias de carrera"),
    "evidence:write": Scope("evidence:write", "Vincular skills con evidencias (experiencias, proyectos…)"),
    "integrations:read": Scope("integrations:read", "Ver tus cuentas externas conectadas (GitHub, LinkedIn…)"),
    "integrations:write": Scope(
        "integrations:write",
        "Sincronizar y desconectar cuentas externas",
    ),
    "suggestions:read": Scope("suggestions:read", "Ver sugerencias para tu perfil"),
    "suggestions:write": Scope("suggestions:write", "Generar y aplicar sugerencias automáticas"),
    "reminders:read": Scope("reminders:read", "Ver recordatorios (certificados expirando, etc.)"),
    "reminders:write": Scope("reminders:write", "Crear, dispatch y dismiss recordatorios"),
}

DEFAULT_SCOPES = (
    "universe:read",
    "universe:write",
    "documents:read",
    "documents:generate",
    "preferences:read",
    "preferences:write",
    "evidence:write",
    "integrations:read",
    "integrations:write",
    "suggestions:read",
    "suggestions:write",
    "reminders:read",
    "reminders:write",
)


def parse_scopes(s: str | None) -> list[str]:
    if not s:
        return []
    return [x for x in s.split() if x]


def validate_scopes(requested: list[str]) -> list[str]:
    return [s for s in requested if s in SCOPES]
