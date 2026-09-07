"""Resolve a diagnostic manifest against the packaged local compatibility snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .contracts import validate_document
from .local_snapshot import load_packaged_snapshot, snapshot_sha256, validate_snapshot
from .resolver import CompatibilityQuery, resolve

_EXPLANATION_SCHEMA_VERSION = "1.0.0"


class LocalExplanationError(ValueError):
    """Raised when a diagnostic cannot be converted into a safe local query."""


def _dedupe_drivers(manifest: dict[str, Any]) -> list[dict[str, str]]:
    target = manifest.get("target") or {}
    rendered: dict[str, dict[str, str]] = {}
    for match in target.get("matches", []):
        for driver in match.get("drivers", []):
            safe = {
                key: str(driver[key])
                for key in ("name", "provider", "version")
                if driver.get(key)
            }
            if not safe:
                continue
            key = json.dumps(safe, sort_keys=True, separators=(",", ":"))
            rendered[key] = safe
    return [rendered[key] for key in sorted(rendered)]


def _connection_paths(manifest: dict[str, Any]) -> list[str]:
    target = manifest["target"]
    paths = sorted(
        {
            str(match.get("connection_path") or "unspecified")
            for match in target.get("matches", [])
        }
    )
    return paths or ["unspecified"]


def _query_for_path(manifest: dict[str, Any], connection_path: str) -> CompatibilityQuery:
    host = manifest["host"]
    platform = manifest["platform"]
    return CompatibilityQuery(
        device_id=manifest["target"]["requested_device_id"],
        host_manufacturer=str(host.get("manufacturer") or "unknown"),
        host_model=str(host.get("model") or "unknown"),
        architecture=platform["architecture"],
        os_family=platform["os_family"],
        os_version=platform["os_version"],
        connection_path=(connection_path,),
    )


def _evidence_sources(snapshot: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    observation_ids = set(result["observation_ids"])
    statement_ids = set(result["support"]["statement_ids"])
    sources: list[dict[str, Any]] = []

    for record in snapshot["observations"]:
        if record["observation_id"] not in observation_ids:
            continue
        for source in record["evidence"]["sources"]:
            sources.append(
                {
                    "record_id": record["observation_id"],
                    "record_kind": "observation",
                    "source_type": record["evidence"]["source_type"],
                    "source_url": source["source_url"],
                    "source_title": source["source_title"],
                    "limitations": record["limitations"],
                }
            )

    for record in snapshot["support_statements"]:
        if record["statement_id"] not in statement_ids:
            continue
        for source in record["evidence"]["sources"]:
            sources.append(
                {
                    "record_id": record["statement_id"],
                    "record_kind": "support_statement",
                    "source_type": record["evidence"]["source_type"],
                    "source_url": source["source_url"],
                    "source_title": source["source_title"],
                    "limitations": record["limitations"],
                }
            )

    return sorted(
        sources,
        key=lambda item: (
            item["record_kind"],
            item["record_id"],
            item["source_url"],
        ),
    )


def explain_diagnostic(
    manifest: dict[str, Any],
    *,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a derived local explanation without modifying the diagnostic manifest."""

    validate_document(manifest, source="diagnostic manifest")
    target = manifest.get("target")
    if not isinstance(target, dict):
        raise LocalExplanationError(
            "local explanation requires a target-device diagnostic manifest"
        )

    local_snapshot = snapshot or load_packaged_snapshot()
    validate_snapshot(local_snapshot)
    limitations = {
        "The packaged local snapshot can lag the public website until the CLI is updated.",
        (
            "Collected driver metadata is context-only in Phase 5B and does not alter "
            "resolver matching."
        ),
    }
    if not manifest["host"].get("manufacturer") or not manifest["host"].get("model"):
        limitations.add(
            "Host manufacturer/model metadata is incomplete; exact host matching may be "
            "unavailable."
        )

    if target["collection_status"] != "collected":
        status = "target_collection_unavailable"
        results: list[dict[str, Any]] = []
        limitations.add("No compatibility result was generated because target collection failed.")
    elif target["present"] is not True:
        status = "target_absent"
        results = []
        limitations.add(
            "No compatibility result was generated because the target was not observed."
        )
    else:
        status = "resolved"
        results = []
        for connection_path in _connection_paths(manifest):
            if connection_path == "unspecified":
                limitations.add(
                    "The target connection path is unspecified, so direct-port and hub "
                    "compatibility are not inferred."
                )
            query = _query_for_path(manifest, connection_path)
            resolved = resolve(
                query,
                local_snapshot["observations"],
                local_snapshot["support_statements"],
            )
            results.append(
                {
                    "connection_path": connection_path,
                    "claim_state": resolved["claim_state"],
                    "specificity": resolved["specificity"],
                    "is_relaxed": resolved["is_relaxed"],
                    "observation_ids": resolved["observation_ids"],
                    "conditions": resolved["conditions"],
                    "support": resolved["support"],
                    "evidence_sources": _evidence_sources(local_snapshot, resolved),
                }
            )

    explanation = {
        "record_type": "local_compatibility_explanation",
        "schema_version": _EXPLANATION_SCHEMA_VERSION,
        "generated_from_diagnostic": manifest["generated_at"],
        "target_device_id": target["requested_device_id"],
        "status": status,
        "snapshot": {
            "format_version": local_snapshot["format_version"],
            "sha256": snapshot_sha256(local_snapshot),
            "observation_count": local_snapshot["observation_count"],
            "support_statement_count": local_snapshot["support_statement_count"],
        },
        "driver_context": {
            "status": target["driver_metadata_status"],
            "drivers": _dedupe_drivers(manifest),
        },
        "results": results,
        "limitations": sorted(limitations),
    }
    validate_document(explanation, source="local compatibility explanation")
    return explanation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", default="-", help="output JSON path, or - for stdout")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        manifest = json.loads(args.diagnostic.read_text(encoding="utf-8"))
        explanation = explain_diagnostic(manifest)
    except (LocalExplanationError, OSError, ValueError) as exc:
        print(f"local explanation failed: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(explanation, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        sys.stdout.write(rendered)
        return 0

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    print(f"wrote local explanation to {destination}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
