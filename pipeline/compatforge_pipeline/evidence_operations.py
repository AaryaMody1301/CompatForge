"""Phase 7D coverage analytics and prioritized evidence review operations."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .resolver import load_observations, load_support_statements

REPORT_VERSION = 1
PRIORITY_THRESHOLDS = {
    "P0": 450,
    "P1": 300,
    "P2": 180,
    "P3": 0,
}


def _canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _platform_key(family: str, architecture: str) -> str:
    return f"{family}/{architecture}"


def _support_platforms(statement: dict[str, Any]) -> set[str]:
    scope = statement["scope"]
    family = scope["operating_system"]["family"]
    architecture = scope["architecture"]
    architectures = ("x86_64", "arm64") if architecture == "any" else (architecture,)
    return {_platform_key(family, item) for item in architectures}


def _observation_platform(observation: dict[str, Any]) -> str:
    host = observation["host"]
    return _platform_key(host["operating_system"]["family"], host["architecture"])


def _record_sources(record: dict[str, Any]) -> set[str]:
    evidence = record["evidence"]
    if record["record_type"] == "compatibility_observation":
        return {evidence["source_url"]}
    return {item["source_url"] for item in evidence["sources"]}


def _priority_band(score: int) -> str:
    for priority, threshold in PRIORITY_THRESHOLDS.items():
        if score >= threshold:
            return priority
    return "P3"


def _freshness_index(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for item in report.get("evidence", []):
        key = (item["evidence_kind"], item["evidence_id"])
        index[key] = item
    return index


def _source_health_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["source_url"]: item for item in report.get("checks", [])}


def _source_device_index(freshness_report: dict[str, Any]) -> dict[str, list[str]]:
    return {
        item["source_url"]: sorted(item.get("device_ids", []))
        for item in freshness_report.get("sources", [])
    }


def _source_evidence_index(freshness_report: dict[str, Any]) -> dict[str, list[str]]:
    return {
        item["source_url"]: sorted(item.get("evidence_refs", []))
        for item in freshness_report.get("sources", [])
    }


def _freshness_task(
    *,
    entry: dict[str, Any],
    sources: set[str],
    source_health: dict[str, dict[str, Any]],
    changed_sources: set[str],
) -> dict[str, Any] | None:
    status = entry["freshness_status"]
    if status not in {"aging", "stale"}:
        return None

    age_days = int(entry["age_days"])
    if status == "stale":
        score = 300 + min(max(age_days - 365, 0), 180)
        task_type = "stale_evidence"
    else:
        score = 180 + min(max(age_days - 180, 0), 185)
        task_type = "aging_evidence"

    reasons = [f"{status} evidence is {age_days} days old"]
    degraded_sources = sorted(
        url for url in sources if url in source_health and not source_health[url].get("ok", False)
    )
    if degraded_sources:
        score += 100
        reasons.append("one or more referenced sources are currently unreachable")
    semantic_sources = sorted(url for url in sources if url in changed_sources)
    if semantic_sources:
        score += 120
        reasons.append("a permitted vendor adapter reported a semantic source change")

    score = min(score, 599)
    return {
        "priority": _priority_band(score),
        "score": score,
        "task_type": task_type,
        "device_id": entry["device_id"],
        "reference": f"{entry['evidence_kind']}:{entry['evidence_id']}",
        "reasons": reasons,
        "source_urls": sorted(sources),
        "age_days": age_days,
    }


def build_operations_report(
    *,
    observations: list[dict[str, Any]],
    support_statements: list[dict[str, Any]],
    freshness_report: dict[str, Any],
    source_check_report: dict[str, Any],
    vendor_change_report: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic Phase 7D review dashboard and work queue."""
    freshness = _freshness_index(freshness_report)
    source_health = _source_health_index(source_check_report)
    source_devices = _source_device_index(freshness_report)
    source_evidence = _source_evidence_index(freshness_report)

    changed_sources = {
        item["source_url"]
        for item in vendor_change_report.get("changes", [])
        if item.get("status") == "changed"
    }

    observations_by_device: dict[str, list[dict[str, Any]]] = defaultdict(list)
    support_by_device: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        observations_by_device[observation["device_id"]].append(observation)
    for statement in support_statements:
        support_by_device[statement["device_id"]].append(statement)

    device_ids = sorted(set(observations_by_device) | set(support_by_device))
    devices: dict[str, dict[str, Any]] = {}
    tasks: list[dict[str, Any]] = []

    for device_id in device_ids:
        device_observations = observations_by_device[device_id]
        device_support = support_by_device[device_id]
        observed_platforms = {_observation_platform(item) for item in device_observations}
        vendor_platforms: set[str] = set()
        for statement in device_support:
            vendor_platforms.update(_support_platforms(statement))

        corroborated = observed_platforms & vendor_platforms
        vendor_only = vendor_platforms - observed_platforms
        observed_only = observed_platforms - vendor_platforms

        evidence_records = [*device_observations, *device_support]
        source_urls: set[str] = set()
        freshness_counts = Counter({"fresh": 0, "aging": 0, "stale": 0})
        outcomes = Counter()
        connection_kinds: set[str] = set()

        for record in evidence_records:
            source_urls.update(_record_sources(record))
            if record["record_type"] == "compatibility_observation":
                evidence_kind = "observation"
                evidence_id = record["observation_id"]
                outcomes[record["outcome"]] += 1
                connection_kinds.update(item["kind"] for item in record["connection_path"])
            else:
                evidence_kind = "support_statement"
                evidence_id = record["statement_id"]
                connection_kinds.add(record["scope"]["connection"]["kind"])

            freshness_entry = freshness.get((evidence_kind, evidence_id))
            if freshness_entry is not None:
                freshness_counts[freshness_entry["freshness_status"]] += 1
                task = _freshness_task(
                    entry=freshness_entry,
                    sources=_record_sources(record),
                    source_health=source_health,
                    changed_sources=changed_sources,
                )
                if task is not None:
                    tasks.append(task)

        for platform in sorted(vendor_only):
            score = 140
            tasks.append(
                {
                    "priority": _priority_band(score),
                    "score": score,
                    "task_type": "reproduction_gap",
                    "device_id": device_id,
                    "reference": platform,
                    "reasons": [
                        "vendor support covers this platform but no reviewed reproduction exists"
                    ],
                    "source_urls": sorted(source_urls),
                    "age_days": None,
                }
            )

        devices[device_id] = {
            "evidence_records": len(evidence_records),
            "observations": len(device_observations),
            "support_statements": len(device_support),
            "source_count": len(source_urls),
            "freshness": dict(freshness_counts),
            "platforms": {
                "observed": sorted(observed_platforms),
                "vendor_supported": sorted(vendor_platforms),
                "corroborated": sorted(corroborated),
                "vendor_only": sorted(vendor_only),
                "observed_only": sorted(observed_only),
            },
            "outcomes": dict(sorted(outcomes.items())),
            "connection_kinds": sorted(connection_kinds),
        }

    for check in source_check_report.get("checks", []):
        if check.get("ok", False):
            continue
        score = 450
        source_url = check["source_url"]
        tasks.append(
            {
                "priority": _priority_band(score),
                "score": score,
                "task_type": "source_health",
                "device_id": None,
                "reference": source_url,
                "device_ids": sorted(check.get("device_ids", [])),
                "evidence_refs": sorted(check.get("evidence_refs", [])),
                "reasons": [
                    f"source check failed: {check.get('error') or check.get('status_code')}"
                ],
                "source_urls": [source_url],
                "age_days": None,
            }
        )

    for change in vendor_change_report.get("changes", []):
        status = change.get("status")
        if status not in {"changed", "missing_baseline"}:
            continue
        source_url = change["source_url"]
        score = 500 if status == "changed" else 350
        changed_fields = change.get("changed_fields", [])
        reason = (
            "vendor semantic facts changed: " + ", ".join(changed_fields)
            if status == "changed"
            else "permitted vendor adapter has no reviewed semantic baseline"
        )
        tasks.append(
            {
                "priority": _priority_band(score),
                "score": score,
                "task_type": "vendor_semantic_change",
                "device_id": None,
                "reference": change["adapter"],
                "device_ids": source_devices.get(source_url, []),
                "evidence_refs": source_evidence.get(source_url, []),
                "reasons": [reason],
                "source_urls": [source_url],
                "age_days": None,
            }
        )

    tasks.sort(
        key=lambda item: (
            -item["score"],
            item["task_type"],
            item.get("device_id") or "",
            item["reference"],
        )
    )
    priority_counts = Counter(item["priority"] for item in tasks)
    task_counts = Counter(item["task_type"] for item in tasks)

    observed_platforms = sum(len(item["platforms"]["observed"]) for item in devices.values())
    vendor_platforms = sum(
        len(item["platforms"]["vendor_supported"]) for item in devices.values()
    )
    corroborated_platforms = sum(
        len(item["platforms"]["corroborated"]) for item in devices.values()
    )
    vendor_only_platforms = sum(
        len(item["platforms"]["vendor_only"]) for item in devices.values()
    )

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "as_of": freshness_report["as_of"],
        "inputs": {
            "freshness_report_sha256": freshness_report.get("report_sha256"),
            "vendor_change_report_sha256": vendor_change_report.get("report_sha256"),
            "source_checks_checked_at": source_check_report.get("checked_at"),
        },
        "summary": {
            "devices": len(devices),
            "evidence_records": len(observations) + len(support_statements),
            "observed_platform_cells": observed_platforms,
            "vendor_platform_cells": vendor_platforms,
            "corroborated_platform_cells": corroborated_platforms,
            "vendor_only_platform_cells": vendor_only_platforms,
            "work_items": len(tasks),
            "priority_counts": dict(sorted(priority_counts.items())),
            "task_counts": dict(sorted(task_counts.items())),
        },
        "devices": devices,
        "work_queue": tasks,
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    priorities = summary["priority_counts"]
    lines = [
        "# CompatForge evidence operations",
        "",
        f"As of `{report['as_of']}`.",
        "",
        "## Coverage dashboard",
        "",
        f"- Devices with reviewed evidence: **{summary['devices']}**",
        f"- Evidence records: **{summary['evidence_records']}**",
        f"- Observed platform cells: **{summary['observed_platform_cells']}**",
        f"- Vendor-supported platform cells: **{summary['vendor_platform_cells']}**",
        f"- Corroborated platform cells: **{summary['corroborated_platform_cells']}**",
        f"- Vendor-only reproduction gaps: **{summary['vendor_only_platform_cells']}**",
        f"- Work items: **{summary['work_items']}**",
        "- Priorities: "
        + ", ".join(f"{key}={priorities.get(key, 0)}" for key in ("P0", "P1", "P2", "P3")),
        "",
        "| Device | Obs | Support | Sources | Platforms obs/vendor/both/gap | Fresh/Aging/Stale |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]

    for device_id, device in report["devices"].items():
        platforms = device["platforms"]
        freshness = device["freshness"]
        platform_summary = (
            f"{len(platforms['observed'])}/{len(platforms['vendor_supported'])}/"
            f"{len(platforms['corroborated'])}/{len(platforms['vendor_only'])}"
        )
        freshness_summary = (
            f"{freshness.get('fresh', 0)}/{freshness.get('aging', 0)}/"
            f"{freshness.get('stale', 0)}"
        )
        lines.append(
            f"| `{device_id}` | {device['observations']} | {device['support_statements']} | "
            f"{device['source_count']} | {platform_summary} | {freshness_summary} |"
        )

    lines.extend(
        [
            "",
            "## Prioritized work queue",
            "",
            "| Priority | Score | Task | Device | Reference |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    if not report["work_queue"]:
        lines.append("| - | - | none | - | - |")
    else:
        for item in report["work_queue"][:50]:
            device = f"`{item['device_id']}`" if item.get("device_id") else "multiple/none"
            lines.append(
                f"| {item['priority']} | {item['score']} | `{item['task_type']}` | "
                f"{device} | `{item['reference']}` |"
            )

    lines.extend(
        [
            "",
            "Priority scoring is deterministic review triage only; it never changes evidence.",
            "",
            f"Report SHA-256: `{report['report_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build coverage dashboard and priority queue")
    build.add_argument("--observations", type=Path, nargs="+", required=True)
    build.add_argument("--support", type=Path, nargs="+", required=True)
    build.add_argument("--freshness", type=Path, required=True)
    build.add_argument("--source-checks", type=Path, required=True)
    build.add_argument("--vendor-changes", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--summary", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    observations = load_observations(args.observations)
    support_statements = load_support_statements(args.support)
    report = build_operations_report(
        observations=observations,
        support_statements=support_statements,
        freshness_report=_load_json(args.freshness),
        source_check_report=_load_json(args.source_checks),
        vendor_change_report=_load_json(args.vendor_changes),
    )
    _write_json(args.output, report)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
