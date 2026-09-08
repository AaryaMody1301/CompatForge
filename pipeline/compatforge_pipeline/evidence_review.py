"""Read-only Phase 7 evidence freshness and upstream source review tooling."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .resolver import load_observations, load_support_statements

REPORT_VERSION = 1
FRESH_MAX_DAYS = 180
AGING_MAX_DAYS = 365
USER_AGENT = "CompatForge-evidence-review/1.0"


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a timezone: {value}")
    return parsed.astimezone(UTC)


def _canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def classify_freshness(age_days: int) -> str:
    if age_days < 0:
        raise ValueError("evidence age cannot be negative")
    if age_days <= FRESH_MAX_DAYS:
        return "fresh"
    if age_days <= AGING_MAX_DAYS:
        return "aging"
    return "stale"


def _record_sources(record: dict[str, Any]) -> list[dict[str, str]]:
    evidence = record["evidence"]
    if record["record_type"] == "compatibility_observation":
        return [
            {
                "source_url": evidence["source_url"],
                "source_title": evidence["source_title"],
            }
        ]
    return sorted(
        (
            {
                "source_url": source["source_url"],
                "source_title": source["source_title"],
            }
            for source in evidence["sources"]
        ),
        key=lambda item: (item["source_url"], item["source_title"]),
    )


def _freshness_entry(
    record: dict[str, Any],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    is_observation = record["record_type"] == "compatibility_observation"
    evidence_kind = "observation" if is_observation else "support_statement"
    evidence_id = record["observation_id"] if is_observation else record["statement_id"]
    evidence_at_raw = record["observed_at"] if is_observation else record["reviewed_at"]
    evidence_at = _parse_timestamp(evidence_at_raw)
    age_days = (as_of.date() - evidence_at.date()).days
    if age_days < 0:
        raise ValueError(
            f"{evidence_kind} {evidence_id} is future-dated relative to {as_of.isoformat()}"
        )
    return {
        "evidence_kind": evidence_kind,
        "evidence_id": evidence_id,
        "device_id": record["device_id"],
        "evidence_at": evidence_at_raw,
        "age_days": age_days,
        "freshness_status": classify_freshness(age_days),
        "sources": _record_sources(record),
    }


def build_freshness_report(
    *,
    observation_paths: list[Path],
    support_paths: list[Path],
    as_of: str,
) -> dict[str, Any]:
    as_of_dt = _parse_timestamp(as_of)
    observations = load_observations(observation_paths)
    support_statements = load_support_statements(support_paths)
    entries = [
        *(_freshness_entry(record, as_of=as_of_dt) for record in observations),
        *(_freshness_entry(record, as_of=as_of_dt) for record in support_statements),
    ]
    entries.sort(key=lambda item: (item["device_id"], item["evidence_kind"], item["evidence_id"]))

    summary = {
        "total": len(entries),
        "fresh": sum(item["freshness_status"] == "fresh" for item in entries),
        "aging": sum(item["freshness_status"] == "aging" for item in entries),
        "stale": sum(item["freshness_status"] == "stale" for item in entries),
        "observations": len(observations),
        "support_statements": len(support_statements),
    }

    by_device: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["device_id"]].append(entry)
    for device_id in sorted(grouped):
        device_entries = grouped[device_id]
        by_device[device_id] = {
            "total": len(device_entries),
            "observations": sum(item["evidence_kind"] == "observation" for item in device_entries),
            "support_statements": sum(
                item["evidence_kind"] == "support_statement" for item in device_entries
            ),
            "fresh": sum(item["freshness_status"] == "fresh" for item in device_entries),
            "aging": sum(item["freshness_status"] == "aging" for item in device_entries),
            "stale": sum(item["freshness_status"] == "stale" for item in device_entries),
            "newest_age_days": min(item["age_days"] for item in device_entries),
            "oldest_age_days": max(item["age_days"] for item in device_entries),
        }

    source_refs: dict[str, dict[str, Any]] = {}
    for entry in entries:
        evidence_ref = f"{entry['evidence_kind']}:{entry['evidence_id']}"
        for source in entry["sources"]:
            item = source_refs.setdefault(
                source["source_url"],
                {
                    "source_url": source["source_url"],
                    "source_titles": set(),
                    "evidence_refs": set(),
                    "device_ids": set(),
                },
            )
            item["source_titles"].add(source["source_title"])
            item["evidence_refs"].add(evidence_ref)
            item["device_ids"].add(entry["device_id"])

    sources = [
        {
            "source_url": item["source_url"],
            "source_titles": sorted(item["source_titles"]),
            "evidence_refs": sorted(item["evidence_refs"]),
            "device_ids": sorted(item["device_ids"]),
        }
        for item in source_refs.values()
    ]
    sources.sort(key=lambda item: item["source_url"])

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "as_of": as_of_dt.isoformat().replace("+00:00", "Z"),
        "thresholds_days": {
            "fresh_max": FRESH_MAX_DAYS,
            "aging_max": AGING_MAX_DAYS,
        },
        "summary": summary,
        "devices": by_device,
        "review_queue": {
            "aging": [
                item["evidence_id"] for item in entries if item["freshness_status"] == "aging"
            ],
            "stale": [
                item["evidence_id"] for item in entries if item["freshness_status"] == "stale"
            ],
        },
        "evidence": entries,
        "sources": sources,
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# CompatForge evidence review",
        "",
        f"As of `{report['as_of']}`.",
        "",
        "## Freshness",
        "",
        f"- Total evidence records: **{summary['total']}**",
        f"- Fresh: **{summary['fresh']}**",
        f"- Aging: **{summary['aging']}**",
        f"- Stale: **{summary['stale']}**",
        f"- Observations: **{summary['observations']}**",
        f"- Support statements: **{summary['support_statements']}**",
        "",
        "## Device coverage",
        "",
        "| Device | Total | Observations | Support | Fresh | Aging | Stale |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for device_id, metrics in report["devices"].items():
        lines.append(
            f"| `{device_id}` | {metrics['total']} | {metrics['observations']} | "
            f"{metrics['support_statements']} | {metrics['fresh']} | "
            f"{metrics['aging']} | {metrics['stale']} |"
        )

    lines.extend(["", "## Review queue", ""])
    aging = report["review_queue"]["aging"]
    stale = report["review_queue"]["stale"]
    lines.append(
        "- Aging: " + (", ".join(f"`{item}`" for item in aging) if aging else "none")
    )
    lines.append(
        "- Stale: " + (", ".join(f"`{item}`" for item in stale) if stale else "none")
    )
    lines.extend(
        [
            "",
            f"Report SHA-256: `{report['report_sha256']}`",
            "",
            "This report is review input only. It does not rewrite evidence or publish changes.",
            "",
        ]
    )
    return "\n".join(lines)


def _request_once(url: str, *, method: str, timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if method == "GET":
            response.read(1)
        return {
            "status_code": response.status,
            "final_url": response.geturl(),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }


def check_source(url: str, *, timeout_seconds: float) -> dict[str, Any]:
    try:
        result = _request_once(url, method="HEAD", timeout_seconds=timeout_seconds)
        return {"ok": 200 <= result["status_code"] < 400, **result, "error": None}
    except urllib.error.HTTPError as exc:
        if exc.code not in {405, 501}:
            return {
                "ok": False,
                "status_code": exc.code,
                "final_url": exc.geturl(),
                "etag": exc.headers.get("ETag") if exc.headers else None,
                "last_modified": exc.headers.get("Last-Modified") if exc.headers else None,
                "error": f"http_{exc.code}",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "status_code": None,
            "final_url": url,
            "etag": None,
            "last_modified": None,
            "error": type(exc).__name__,
        }

    try:
        result = _request_once(url, method="GET", timeout_seconds=timeout_seconds)
        return {"ok": 200 <= result["status_code"] < 400, **result, "error": None}
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status_code": exc.code,
            "final_url": exc.geturl(),
            "etag": exc.headers.get("ETag") if exc.headers else None,
            "last_modified": exc.headers.get("Last-Modified") if exc.headers else None,
            "error": f"http_{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "status_code": None,
            "final_url": url,
            "etag": None,
            "last_modified": None,
            "error": type(exc).__name__,
        }


def build_source_check_report(
    *,
    freshness_report: dict[str, Any],
    checked_at: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    checked_at_dt = _parse_timestamp(checked_at)
    checks = []
    for source in freshness_report["sources"]:
        result = check_source(source["source_url"], timeout_seconds=timeout_seconds)
        checks.append(
            {
                "source_url": source["source_url"],
                "evidence_refs": source["evidence_refs"],
                "device_ids": source["device_ids"],
                **result,
            }
        )
    checks.sort(key=lambda item: item["source_url"])
    return {
        "report_version": REPORT_VERSION,
        "checked_at": checked_at_dt.isoformat().replace("+00:00", "Z"),
        "freshness_report_sha256": freshness_report["report_sha256"],
        "summary": {
            "total": len(checks),
            "reachable": sum(item["ok"] for item in checks),
            "unreachable": sum(not item["ok"] for item in checks),
        },
        "checks": checks,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    report = commands.add_parser("report", help="build deterministic freshness and coverage review")
    report.add_argument("--observations", type=Path, nargs="+", required=True)
    report.add_argument("--support", type=Path, nargs="+", required=True)
    report.add_argument("--as-of", required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--summary", type=Path)

    checks = commands.add_parser("check-sources", help="perform read-only upstream source checks")
    checks.add_argument("--report", type=Path, required=True)
    checks.add_argument("--checked-at", required=True)
    checks.add_argument("--timeout-seconds", type=float, default=15.0)
    checks.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "report":
        report = build_freshness_report(
            observation_paths=args.observations,
            support_paths=args.support,
            as_of=args.as_of,
        )
        _write_json(args.output, report)
        if args.summary:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(render_markdown(report), encoding="utf-8")
        return 0

    freshness_report = json.loads(args.report.read_text(encoding="utf-8"))
    source_report = build_source_check_report(
        freshness_report=freshness_report,
        checked_at=args.checked_at,
        timeout_seconds=args.timeout_seconds,
    )
    _write_json(args.output, source_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
