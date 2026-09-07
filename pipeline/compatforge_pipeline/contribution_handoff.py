"""Prepare an explicit, local-only contribution handoff artifact."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .contracts import validate_document

_HANDOFF_SCHEMA_VERSION = "1.0.0"


class ContributionHandoffError(ValueError):
    """Raised when a diagnostic cannot be safely exported for future contribution."""


def _safe_drivers(manifest: dict[str, Any]) -> list[dict[str, str]]:
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
            key = repr(sorted(safe.items()))
            rendered[key] = safe
    return [rendered[key] for key in sorted(rendered)]


def _connection_paths(manifest: dict[str, Any]) -> list[str]:
    target = manifest.get("target") or {}
    return sorted(
        {
            str(match.get("connection_path") or "unspecified")
            for match in target.get("matches", [])
        }
    ) or ["unspecified"]


def _local_results(explanation: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in explanation.get("results", []):
        results.append(
            {
                "connection_path": item["connection_path"],
                "claim_state": item["claim_state"],
                "specificity": item["specificity"],
                "observation_ids": sorted(item["observation_ids"]),
                "support_state": item["support"]["state"],
                "support_statement_ids": sorted(item["support"]["statement_ids"]),
            }
        )
    return sorted(results, key=lambda item: item["connection_path"])


def prepare_contribution_handoff(
    manifest: dict[str, Any],
    explanation: dict[str, Any],
    *,
    approved_export: bool,
    prepared_at: str | None = None,
) -> dict[str, Any]:
    """Create an inspectable local export only after explicit user approval."""

    if not approved_export:
        raise ContributionHandoffError("explicit export approval is required")

    validate_document(manifest, source="diagnostic manifest")
    validate_document(explanation, source="local compatibility explanation")

    target = manifest.get("target")
    if not isinstance(target, dict):
        raise ContributionHandoffError("contribution handoff requires a target-device diagnostic")
    if explanation["target_device_id"] != target["requested_device_id"]:
        raise ContributionHandoffError("diagnostic and explanation target devices do not match")
    if explanation["generated_from_diagnostic"] != manifest["generated_at"]:
        raise ContributionHandoffError(
            "explanation was not generated from this diagnostic manifest"
        )

    host = manifest["host"]
    platform = manifest["platform"]
    safe_host = {
        key: str(host[key])
        for key in ("manufacturer", "model")
        if host.get(key)
    }
    operating_system: dict[str, str] = {
        "family": str(platform["os_family"]),
        "version": str(platform["os_version"]),
    }
    if platform.get("os_build"):
        operating_system["build"] = str(platform["os_build"])

    handoff = {
        "record_type": "contribution_handoff",
        "schema_version": _HANDOFF_SCHEMA_VERSION,
        "prepared_at": prepared_at
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "user_approved_export": True,
        "evidence_ready": False,
        "source_diagnostic_generated_at": manifest["generated_at"],
        "target_device_id": target["requested_device_id"],
        "configuration": {
            "host": safe_host,
            "operating_system": operating_system,
            "architecture": platform["architecture"],
            "target_present": target["present"],
            "connection_paths": _connection_paths(manifest),
            "drivers": _safe_drivers(manifest),
        },
        "local_context": {
            "explanation_status": explanation["status"],
            "snapshot_sha256": explanation["snapshot"]["sha256"],
            "results": _local_results(explanation),
        },
        "privacy": {
            "automatic_upload": False,
            "network_request_performed": False,
            "serial_numbers_in_handoff": False,
            "network_identifiers_in_handoff": False,
            "unrelated_usb_devices_in_handoff": False,
        },
        "limitations": [
            "This handoff is local configuration context, not a compatibility observation.",
            (
                "A future contribution still requires an explicit user-supplied outcome, "
                "reproduction steps, and evidence before publication."
            ),
        ],
    }
    validate_document(handoff, source="contribution handoff")
    return handoff
