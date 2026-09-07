from __future__ import annotations

import json
from pathlib import Path

import pytest
from compatforge_pipeline.contracts import validate_document
from compatforge_pipeline.contribution_handoff import (
    ContributionHandoffError,
    prepare_contribution_handoff,
)
from compatforge_pipeline.local_explain import explain_diagnostic


FIXTURE = Path("data/fixtures/diagnostic_manifest.json")


def _manifest() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_contribution_handoff_requires_explicit_approval() -> None:
    manifest = _manifest()
    explanation = explain_diagnostic(manifest)

    with pytest.raises(ContributionHandoffError, match="explicit export approval"):
        prepare_contribution_handoff(
            manifest,
            explanation,
            approved_export=False,
            prepared_at="2026-09-07T00:00:00Z",
        )


def test_contribution_handoff_is_local_context_not_evidence() -> None:
    manifest = _manifest()
    explanation = explain_diagnostic(manifest)
    handoff = prepare_contribution_handoff(
        manifest,
        explanation,
        approved_export=True,
        prepared_at="2026-09-07T00:00:00Z",
    )

    validate_document(handoff)
    assert handoff["user_approved_export"] is True
    assert handoff["evidence_ready"] is False
    assert handoff["privacy"] == {
        "automatic_upload": False,
        "network_request_performed": False,
        "serial_numbers_in_handoff": False,
        "network_identifiers_in_handoff": False,
        "unrelated_usb_devices_in_handoff": False,
    }
    assert handoff["target_device_id"] == manifest["target"]["requested_device_id"]
    assert "agent" not in handoff
    assert "warnings" not in handoff


def test_contribution_handoff_rejects_mismatched_explanation() -> None:
    manifest = _manifest()
    explanation = explain_diagnostic(manifest)
    explanation["target_device_id"] = "usb:21A9:1005"

    with pytest.raises(ContributionHandoffError, match="target devices do not match"):
        prepare_contribution_handoff(
            manifest,
            explanation,
            approved_export=True,
            prepared_at="2026-09-07T00:00:00Z",
        )
