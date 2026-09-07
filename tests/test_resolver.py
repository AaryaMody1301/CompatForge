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
