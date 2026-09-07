from compatforge_pipeline.contracts import validate_document
from compatforge_pipeline.local_explain import explain_diagnostic


def _diagnostic(*, present: bool = True) -> dict:
    return {
        "record_type": "diagnostic_manifest",
        "schema_version": "1.1.0",
        "agent": {"name": "compatforge-diagnose", "version": "synthetic-test"},
        "generated_at": "2026-09-07T00:00:00Z",
        "platform": {
            "os_family": "windows",
            "os_name": "Windows 11",
            "os_version": "11",
            "os_build": "25H2",
            "architecture": "arm64",
        },
        "host": {"manufacturer": "Acer", "model": "Aspire 14 AI (2025)"},
        "target": {
            "requested_device_id": "usb:0403:6001",
            "collection_status": "collected",
            "present": present,
            "match_count": 1 if present else 0,
            "driver_metadata_status": "collected" if present else "not_observed",
            "matches": (
                [
                    {
                        "device_id": "usb:0403:6001",
                        "connection_path": "unspecified",
                        "status": "present",
                        "drivers": [
                            {
                                "name": "FTDI VCP",
                                "provider": "FTDI",
                                "version": "2.12.36.20A",
                            }
                        ],
                    }
                ]
                if present
                else []
            ),
        },
        "privacy": {
            "collection_mode": "local_only",
            "scope": "target_device_only",
            "serial_numbers_in_manifest": False,
            "network_identifiers_in_manifest": False,
            "unrelated_usb_devices_in_manifest": False,
            "automatic_upload": False,
        },
        "warnings": [],
    }


def test_local_explanation_reuses_packaged_resolver_evidence() -> None:
    explanation = explain_diagnostic(_diagnostic())
    validate_document(explanation)
    assert explanation["status"] == "resolved"
    assert explanation["driver_context"]["status"] == "collected"
    assert explanation["driver_context"]["drivers"][0]["version"] == "2.12.36.20A"

    result = explanation["results"][0]
    assert result["connection_path"] == "unspecified"
    assert result["claim_state"] == "works_with_conditions"
    assert result["specificity"] == "exact"
    assert result["observation_ids"] == ["obs_avrdude_ft232r_win11arm64"]
    assert result["support"]["state"] == "supported_with_conditions"
    assert result["support"]["statement_ids"] == ["sup_ftdi_ft232r_win11_arm64"]
    assert any("avrdude" in item["source_url"] for item in result["evidence_sources"])
    assert any("ftdichip.com" in item["source_url"] for item in result["evidence_sources"])


def test_local_explanation_does_not_invent_result_for_absent_target() -> None:
    explanation = explain_diagnostic(_diagnostic(present=False))
    validate_document(explanation)
    assert explanation["status"] == "target_absent"
    assert explanation["results"] == []
    assert explanation["driver_context"] == {"status": "not_observed", "drivers": []}
