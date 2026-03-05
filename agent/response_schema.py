from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import ValidationError, validate


SCHEMA_DIR = Path(__file__).parent / "schemas"


class SchemaValidationError(ValueError):
    pass


def _load_schema(schema_name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        raise SchemaValidationError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_response(schema_name: str, payload: Dict[str, Any]) -> None:
    schema = _load_schema(schema_name)
    try:
        validate(instance=payload, schema=schema)
    except ValidationError as exc:
        raise SchemaValidationError(str(exc)) from exc


def validate_action_or_clarify(payload: Dict[str, Any]) -> None:
    validate_response("action_or_clarify", payload)


def validate_enemy_action(payload: Dict[str, Any]) -> None:
    validate_response("enemy_action", payload)
