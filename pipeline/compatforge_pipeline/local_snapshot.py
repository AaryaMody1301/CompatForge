"""Build, load, and verify the packaged local compatibility snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from .resolver import load_observations, load_support_statements

_FORMAT_VERSION = "1.0.0"
_RESOURCE_DIR = "resources"
_RESOURCE_NAME = "local_snapshot.json"


class LocalSnapshotError(ValueError):
    """Raised when the packaged local snapshot is malformed or out of sync."""


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def snapshot_sha256(snapshot: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 for a validated local snapshot."""

    validate_snapshot(snapshot)
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def _normalized_sources(evidence: dict[str, Any]) -> list[dict[str, str]]:
    raw_sources = evidence.get("sources")
    if isinstance(raw_sources, list):
        sources = [
            {
                "source_url": str(item["source_url"]),
                "source_title": str(item["source_title"]),
            }
            for item in raw_sources
            if isinstance(item, dict) and item.get("source_url") and item.get("source_title")
        ]
    else:
        sources = [
            {
                "source_url": str(evidence["source_url"]),
                "source_title": str(evidence["source_title"]),
            }
        ]
    return sorted(sources, key=lambda item: (item["source_url"], item["source_title"]))


def _project_observation(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation_id": record["observation_id"],
        "device_id": record["device_id"],
        "host": record["host"],
        "connection_path": [{"kind": item["kind"]} for item in record["connection_path"]],
        "outcome": record["outcome"],
        "conditions": sorted(set(record.get("conditions", []))),
        "evidence": {
            "source_type": record["evidence"]["source_type"],
            "sources": _normalized_sources(record["evidence"]),
        },
        "limitations": sorted(set(record.get("limitations", []))),
    }


def _project_support(record: dict[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "statement_id": record["statement_id"],
        "device_id": record["device_id"],
        "scope": record["scope"],
        "support_status": record["support_status"],
        "conditions": sorted(set(record.get("conditions", []))),
        "evidence": {
            "source_type": record["evidence"]["source_type"],
            "sources": _normalized_sources(record["evidence"]),
        },
        "limitations": sorted(set(record.get("limitations", []))),
    }
    for field in ("driver", "software"):
        if field in record:
            projected[field] = record[field]
    return projected


def build_snapshot(
    observation_paths: list[Path], support_paths: list[Path]
) -> dict[str, Any]:
    """Project reviewed source records into the deterministic local resolver format."""

    observations = sorted(
        (_project_observation(item) for item in load_observations(observation_paths)),
        key=lambda item: item["observation_id"],
    )
    support = sorted(
        (_project_support(item) for item in load_support_statements(support_paths)),
        key=lambda item: item["statement_id"],
    )
    snapshot = {
        "format_version": _FORMAT_VERSION,
        "observation_count": len(observations),
        "support_statement_count": len(support),
        "observations": observations,
        "support_statements": support,
    }
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    """Validate the compact internal snapshot without treating it as a public evidence record."""

    if not isinstance(snapshot, dict):
        raise LocalSnapshotError("local snapshot must be a JSON object")
    if snapshot.get("format_version") != _FORMAT_VERSION:
        raise LocalSnapshotError("unsupported local snapshot format_version")

    observations = snapshot.get("observations")
    support = snapshot.get("support_statements")
    if not isinstance(observations, list) or not isinstance(support, list):
        raise LocalSnapshotError("local snapshot record collections must be arrays")
    if snapshot.get("observation_count") != len(observations):
        raise LocalSnapshotError("local snapshot observation_count does not match records")
    if snapshot.get("support_statement_count") != len(support):
        raise LocalSnapshotError("local snapshot support_statement_count does not match records")

    observation_ids: list[str] = []
    for record in observations:
        if not isinstance(record, dict):
            raise LocalSnapshotError("local snapshot observation must be an object")
        required = {
            "observation_id",
            "device_id",
            "host",
            "connection_path",
            "outcome",
            "conditions",
            "evidence",
            "limitations",
        }
        if not required.issubset(record):
            raise LocalSnapshotError("local snapshot observation is missing required fields")
        observation_ids.append(str(record["observation_id"]))

    statement_ids: list[str] = []
    for record in support:
        if not isinstance(record, dict):
            raise LocalSnapshotError("local snapshot support statement must be an object")
        required = {
            "statement_id",
            "device_id",
            "scope",
            "support_status",
            "conditions",
            "evidence",
            "limitations",
        }
        if not required.issubset(record):
            raise LocalSnapshotError("local snapshot support statement is missing required fields")
        statement_ids.append(str(record["statement_id"]))

    if observation_ids != sorted(observation_ids) or len(observation_ids) != len(set(observation_ids)):
        raise LocalSnapshotError("local snapshot observation IDs must be unique and sorted")
    if statement_ids != sorted(statement_ids) or len(statement_ids) != len(set(statement_ids)):
        raise LocalSnapshotError("local snapshot support statement IDs must be unique and sorted")


def load_packaged_snapshot() -> dict[str, Any]:
    """Load the reviewed local snapshot bundled with the Python package."""

    resource = files("compatforge_pipeline").joinpath(_RESOURCE_DIR).joinpath(_RESOURCE_NAME)
    try:
        payload = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalSnapshotError("packaged local snapshot could not be loaded") from exc
    validate_snapshot(payload)
    return payload


def render_snapshot(snapshot: dict[str, Any]) -> str:
    validate_snapshot(snapshot)
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def verify_packaged_snapshot(
    observation_paths: list[Path], support_paths: list[Path]
) -> str:
    """Require the bundled snapshot to equal a fresh deterministic projection."""

    expected = build_snapshot(observation_paths, support_paths)
    packaged = load_packaged_snapshot()
    if _canonical_json(expected) != _canonical_json(packaged):
        raise LocalSnapshotError(
            "packaged local snapshot is stale; rebuild it from the reviewed evidence corpus"
        )
    return snapshot_sha256(packaged)


def _add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--observations", nargs="+", type=Path, required=True)
    parser.add_argument("--support", nargs="+", type=Path, required=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build the compact snapshot from reviewed evidence")
    _add_source_arguments(build)
    build.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify", help="verify the packaged snapshot matches evidence")
    _add_source_arguments(verify)

    subparsers.add_parser("info", help="print metadata for the packaged snapshot")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "build":
            snapshot = build_snapshot(args.observations, args.support)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_snapshot(snapshot), encoding="utf-8")
            print(f"wrote local snapshot to {args.output}", file=sys.stderr)
            return 0
        if args.command == "verify":
            digest = verify_packaged_snapshot(args.observations, args.support)
            print(f"verified packaged local snapshot sha256={digest}")
            return 0

        snapshot = load_packaged_snapshot()
        print(
            json.dumps(
                {
                    "format_version": snapshot["format_version"],
                    "observation_count": snapshot["observation_count"],
                    "support_statement_count": snapshot["support_statement_count"],
                    "sha256": snapshot_sha256(snapshot),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (LocalSnapshotError, OSError, ValueError) as exc:
        print(f"local snapshot failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
