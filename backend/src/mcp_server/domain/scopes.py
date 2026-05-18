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
}

DEFAULT_SCOPES = (
    "universe:read",
    "universe:write",
    "documents:generate",
)


def parse_scopes(s: str | None) -> list[str]:
    if not s:
        return []
    return [x for x in s.split() if x]


def validate_scopes(requested: list[str]) -> list[str]:
    return [s for s in requested if s in SCOPES]
