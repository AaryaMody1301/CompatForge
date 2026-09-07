"""JSON Schema loading and validation for public CompatForge contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"

_SCHEMA_BY_RECORD_TYPE = {
    "device": "device.schema.json",
    "compatibility_observation": "observation.schema.json",
    "compatibility_support_statement": "support-statement.schema.json",
}


class ContractValidationError(ValueError):
    """Raised when a document violates a CompatForge public contract."""


def load_schema(record_type: str) -> dict[str, Any]:
    """Load a schema by its public record type."""

    try:
        schema_name = _SCHEMA_BY_RECORD_TYPE[record_type]
    except KeyError as exc:
        raise ContractValidationError(f"Unsupported record_type: {record_type!r}") from exc

    with (SCHEMA_DIR / schema_name).open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_document(document: dict[str, Any], *, source: str = "<memory>") -> None:
    """Validate one document and raise a compact deterministic error on failure."""

    record_type = document.get("record_type")
    if not isinstance(record_type, str):
        raise ContractValidationError(f"{source}: record_type must be present and be a string")

    schema = load_schema(record_type)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if not errors:
        return

    rendered = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        rendered.append(f"{location}: {error.message}")
    raise ContractValidationError(f"{source}: " + "; ".join(rendered))
