"""Deterministic compatibility evidence resolver."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import validate_document
from .validate import iter_json_files

_VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")


@dataclass(frozen=True, slots=True)
class CompatibilityQuery:
    """Normalized compatibility question presented to the resolver."""

    device_id: str
    host_manufacturer: str
    host_model: str
    architecture: str
    os_family: str
    os_version: str
    connection_path: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> CompatibilityQuery:
        host = payload["host"]
        operating_system = host["operating_system"]
        path = tuple(item["kind"] for item in payload["connection_path"])
        if not path:
            raise ValueError("query connection_path must not be empty")
        return cls(
            device_id=payload["device_id"],
            host_manufacturer=host["manufacturer"],
            host_model=host["model"],
            architecture=host["architecture"],
            os_family=operating_system["family"],
            os_version=operating_system["version"],
            connection_path=path,
        )


def _norm(value: str) -> str:
    return value.strip().casefold()


def _load_records(paths: list[Path], record_type: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in iter_json_files(paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("record_type") != record_type:
            continue
        validate_document(payload, source=str(path))
        records.append(payload)
    return records


def load_observations(paths: list[Path]) -> list[dict[str, Any]]:
    return _load_records(paths, "compatibility_observation")


def load_support_statements(paths: list[Path]) -> list[dict[str, Any]]:
    return _load_records(paths, "compatibility_support_statement")


def _observation_matches(
    observation: dict[str, Any],
    query: CompatibilityQuery,
    *,
    ignore_host: bool,
    ignore_os_version: bool,
) -> bool:
    host = observation["host"]
    operating_system = host["operating_system"]
    path = tuple(item["kind"] for item in observation["connection_path"])
    if observation["device_id"] != query.device_id:
        return False
    if host["architecture"] != query.architecture:
        return False
    if operating_system["family"] != query.os_family:
        return False
    if path != query.connection_path:
        return False
    if not ignore_os_version and _norm(operating_system["version"]) != _norm(query.os_version):
        return False
    if ignore_host:
        return True
    return (
        _norm(host["manufacturer"]) == _norm(query.host_manufacturer)
        and _norm(host["model"]) == _norm(query.host_model)
    )


def _best_observations(
    observations: list[dict[str, Any]], query: CompatibilityQuery
) -> tuple[list[dict[str, Any]], str]:
    tiers = (
        ("exact", False, False),
        ("host_relaxed", True, False),
        ("os_version_relaxed", True, True),
    )
    for specificity, ignore_host, ignore_version in tiers:
        matches = [
            item
            for item in observations
            if _observation_matches(
                item,
                query,
                ignore_host=ignore_host,
                ignore_os_version=ignore_version,
            )
        ]
        if matches:
            return matches, specificity
    return [], "none"


def _claim_state(observations: list[dict[str, Any]]) -> str:
    if not observations:
        return "unknown"
    outcomes = {item["outcome"] for item in observations}
    has_success = bool(outcomes & {"works", "works_with_conditions"})
    has_failure = "fails" in outcomes
    if has_success and has_failure:
        return "conflicting"
    if has_failure:
        return "fails"
    if "works_with_conditions" in outcomes:
        return "works_with_conditions"
    return "works"


def _numeric_version(value: str) -> tuple[int, ...] | None:
    if not _VERSION_RE.fullmatch(value.strip()):
        return None
    return tuple(int(part) for part in value.strip().split("."))


def _version_matches(rule: dict[str, Any], query_version: str) -> bool:
    mode = rule["version_mode"]
    if mode == "any":
        return True
    if mode in {"exact", "one_of"}:
        return _norm(query_version) in {_norm(item) for item in rule["versions"]}
    minimum = _numeric_version(rule["minimum_version"])
    current = _numeric_version(query_version)
    return minimum is not None and current is not None and current >= minimum


def _support_matches(statement: dict[str, Any], query: CompatibilityQuery) -> bool:
    if statement["device_id"] != query.device_id:
        return False
    scope = statement["scope"]
    if scope["architecture"] not in {"any", query.architecture}:
        return False
    operating_system = scope["operating_system"]
    if operating_system["family"] != query.os_family:
        return False
    if not _version_matches(operating_system, query.os_version):
        return False
    connection_kind = scope["connection"]["kind"]
    return connection_kind == "any_usb" or connection_kind in query.connection_path


def _support_specificity(statement: dict[str, Any], query: CompatibilityQuery) -> int:
    scope = statement["scope"]
    score = 4 if scope["architecture"] == query.architecture else 1
    mode = scope["operating_system"]["version_mode"]
    score += {"exact": 4, "one_of": 4, "minimum": 2, "any": 1}[mode]
    score += 2 if scope["connection"]["kind"] != "any_usb" else 1
    return score


def _best_support(
    statements: list[dict[str, Any]], query: CompatibilityQuery
) -> list[dict[str, Any]]:
    matches = [item for item in statements if _support_matches(item, query)]
    if not matches:
        return []
    best_score = max(_support_specificity(item, query) for item in matches)
    return [item for item in matches if _support_specificity(item, query) == best_score]


def _support_state(statements: list[dict[str, Any]]) -> str:
    if not statements:
        return "unknown"
    states = {item["support_status"] for item in statements}
    positive = bool(states & {"supported", "supported_with_conditions"})
    negative = "unsupported" in states
    if positive and negative:
        return "conflicting"
    if negative:
        return "unsupported"
    if "supported_with_conditions" in states:
        return "supported_with_conditions"
    return "supported"


def _conditions(records: list[dict[str, Any]]) -> list[str]:
    return sorted({condition for item in records for condition in item.get("conditions", [])})


def resolve(
    query: CompatibilityQuery,
    observations: list[dict[str, Any]],
    support_statements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve one query without converting vendor support into observed compatibility."""
    matched_observations, specificity = _best_observations(observations, query)
    matched_support = _best_support(support_statements, query)
    return {
        "claim_state": _claim_state(matched_observations),
        "specificity": specificity,
        "is_relaxed": specificity not in {"exact", "none"},
        "observation_ids": sorted(item["observation_id"] for item in matched_observations),
        "conditions": _conditions(matched_observations),
        "support": {
            "state": _support_state(matched_support),
            "statement_ids": sorted(item["statement_id"] for item in matched_support),
            "conditions": _conditions(matched_support),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, type=Path)
    parser.add_argument("--observations", nargs="*", type=Path, default=[])
    parser.add_argument("--support", nargs="*", type=Path, default=[])
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = json.loads(args.query.read_text(encoding="utf-8"))
    query = CompatibilityQuery.from_mapping(payload)
    result = resolve(
        query,
        load_observations(args.observations),
        load_support_statements(args.support),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
