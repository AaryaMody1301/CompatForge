from dataclasses import replace

import pytest
from compatforge_pipeline.contracts import validate_document
from compatforge_pipeline.resolver import CompatibilityQuery, resolve


def _query(*, os_version: str = "11", manufacturer: str = "Acme", model: str = "Host A"):
    return CompatibilityQuery(
        device_id="usb:1234:0001",
        host_manufacturer=manufacturer,
        host_model=model,
        architecture="x86_64",
        os_family="windows",
        os_version=os_version,
        connection_path=("direct_port",),
    )


def _observation(
    observation_id: str,
    outcome: str,
    *,
    os_version: str = "11",
    manufacturer: str = "Acme",
    model: str = "Host A",
):
    document = {
        "schema_version": "1.0.0",
        "record_type": "compatibility_observation",
        "observation_id": observation_id,
        "device_id": "usb:1234:0001",
        "host": {
            "manufacturer": manufacturer,
            "model": model,
            "architecture": "x86_64",
            "operating_system": {"family": "windows", "version": os_version},
        },
        "connection_path": [{"kind": "direct_port"}],
        "outcome": outcome,
        "evidence": {
            "source_type": "independent_reproduction",
            "source_url": "https://example.com/reproduction",
            "source_title": "Synthetic resolver reproduction",
        },
        "observed_at": "2026-01-01T00:00:00Z",
        "recorded_at": "2026-01-01T00:00:00Z",
    }
    if outcome == "works_with_conditions":
        document["conditions"] = ["Use the direct USB port."]
    validate_document(document)
    return document


def _support(status: str = "supported"):
    document = {
        "schema_version": "1.0.0",
        "record_type": "compatibility_support_statement",
        "statement_id": "sup_synthetic_windows_x64",
        "device_id": "usb:1234:0001",
        "scope": {
            "architecture": "x86_64",
            "operating_system": {
                "family": "windows",
                "version_mode": "one_of",
                "versions": ["10", "11"],
            },
            "connection": {"kind": "any_usb"},
        },
        "support_status": status,
        "evidence": {
            "source_type": "vendor_documentation",
            "sources": [
                {"source_url": "https://example.com/support", "source_title": "Support matrix"}
            ],
            "source_note": "Synthetic support statement for resolver tests.",
        },
        "reviewed_at": "2026-01-01T00:00:00Z",
        "recorded_at": "2026-01-01T00:00:00Z",
    }
    if status == "supported_with_conditions":
        document["conditions"] = ["Install the vendor driver."]
    validate_document(document)
    return document


def test_exact_observation_resolves_working_claim() -> None:
    result = resolve(_query(), [_observation("obs_exact_works", "works")], [])
    assert result["claim_state"] == "works"
    assert result["specificity"] == "exact"
    assert result["is_relaxed"] is False


def test_usb_generation_remains_unchecked_without_observation_evidence() -> None:
    query = replace(_query(), usb_generation="3.0")
    result = resolve(query, [_observation("obs_usb_generation_unknown", "works")], [])

    assert result["claim_state"] == "works"
    assert "usb_generation" in result["unchecked_dimensions"]


def test_failure_and_success_at_same_tier_are_conflicting() -> None:
    result = resolve(
        _query(),
        [
            _observation("obs_conflict_ok", "works"),
            _observation("obs_conflict_fail", "fails"),
        ],
        [],
    )
    assert result["claim_state"] == "conflicting"


def test_host_relaxation_is_explicit() -> None:
    result = resolve(
        _query(),
        [_observation("obs_other_host", "works", manufacturer="Other", model="Host B")],
        [],
    )
    assert result["claim_state"] == "works"
    assert result["specificity"] == "host_relaxed"
    assert result["is_relaxed"] is True


def test_os_version_relaxation_is_only_used_after_more_specific_tiers() -> None:
    result = resolve(
        _query(os_version="11"),
        [_observation("obs_windows_10", "works", os_version="10", model="Host B")],
        [],
    )
    assert result["claim_state"] == "works"
    assert result["specificity"] == "os_version_relaxed"


def test_vendor_support_does_not_become_observed_works() -> None:
    result = resolve(_query(), [], [_support("supported")])
    assert result["claim_state"] == "unknown"
    assert result["support"]["state"] == "supported"


def test_conditional_support_preserves_conditions() -> None:
    result = resolve(_query(), [], [_support("supported_with_conditions")])
    assert result["support"]["state"] == "supported_with_conditions"
    assert result["support"]["conditions"] == ["Install the vendor driver."]


@pytest.mark.parametrize("field,value", [
    ("os_build", "99999"),
    ("driver_name", "Another driver"),
    ("driver_version", "99.0"),
    ("software_name", "Another application"),
    ("software_version", "99.0"),
    ("firmware_version", "99.0"),
])
def test_supplied_configuration_metadata_cannot_be_ignored(field: str, value: str) -> None:
    observation = _observation("obs_metadata", "works")
    observation["host"]["operating_system"]["build"] = "26100"
    observation["driver"] = {"name": "FTDI VCP", "version": "2.1"}
    observation["software"] = {"name": "avrdude", "version": "7.0"}
    observation["firmware_version"] = "1.0"
    query = _query()
    result = resolve(replace(query, **{field: value}), [observation], [])
    assert result["claim_state"] == "unknown"
    assert result["specificity"] == "none"


def test_minimum_version_treats_missing_trailing_zero_as_equal() -> None:
    statement = _support()
    statement["scope"]["operating_system"] = {
        "family": "windows", "version_mode": "minimum", "minimum_version": "10.0",
    }
    assert resolve(_query(os_version="10"), [], [statement])["support"]["state"] == "supported"


def test_query_preserves_path_component_identity_and_metadata() -> None:
    query = CompatibilityQuery.from_mapping({
        "device_id": "usb:1234:0001",
        "host": {"manufacturer": "Acme", "model": "Host A", "architecture": "x86_64",
                 "operating_system": {"family": "windows", "version": "11", "build": "26100"}},
        "connection_path": [{"kind": "usb_hub", "manufacturer": "Acme", "model": "Hub 1"}],
        "driver": {"name": "Driver A", "version": "1.0"},
    })
    assert query.os_build == "26100"
    assert query.driver_name == "Driver A"
    assert query.connection_components[0]["model"] == "Hub 1"


def test_supplied_connection_component_identity_is_not_ignored() -> None:
    query = replace(
        _query(),
        connection_components=({"kind": "direct_port", "model": "Dock Model"},),
    )
    result = resolve(query, [_observation("obs_component_model", "works")], [])

    assert result["claim_state"] == "unknown"
    assert result["specificity"] == "none"
    assert "connection_component_identity" in result["unchecked_dimensions"]


def test_invalid_os_version_cannot_create_relaxed_positive_claim() -> None:
    result = resolve(
        _query(os_version="garbage"),
        [_observation("obs_valid_version", "works", os_version="11")],
        [_support()],
    )
    assert result["claim_state"] == "unknown"
    assert result["support"]["state"] == "unknown"
    assert result["invalid_fields"] == ["os_version"]
