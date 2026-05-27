from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def jsonify(value: Any) -> Any:
    """Serialize a value for JSON output: pydantic → dict, datetime → iso, UUID → str."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonify(v) for v in value]
    return value
