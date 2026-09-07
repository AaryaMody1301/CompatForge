"""Validate CompatForge JSON records from files or directories."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from .contracts import ContractValidationError, validate_document


def iter_json_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Yield JSON files in deterministic path order."""

    discovered: set[Path] = set()
    for path in paths:
        if path.is_dir():
            discovered.update(item for item in path.rglob("*.json") if item.is_file())
        elif path.is_file() and path.suffix.lower() == ".json":
            discovered.add(path)
        else:
            raise FileNotFoundError(f"No JSON file or directory found at {path}")
    yield from sorted(discovered)


def validate_paths(paths: Iterable[Path]) -> int:
    """Validate all JSON documents and return the number checked."""

    checked = 0
    for path in iter_json_files(paths):
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, dict):
            raise ContractValidationError(f"{path}: top-level JSON value must be an object")
        validate_document(document, source=str(path))
        checked += 1
    return checked


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate CompatForge contract records")
    parser.add_argument("paths", nargs="+", type=Path, help="JSON files or directories to validate")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        checked = validate_paths(args.paths)
    except (ContractValidationError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"validation failed: {exc}")
        return 1
    print(f"validated {checked} CompatForge record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
