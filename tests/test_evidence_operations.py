from compatforge_pipeline import evidence_operations


def _observation() -> dict:
    return {
        "schema_version": "1.0.0",
        "record_type": "compatibility_observation",
        "observation_id": "obs_test_win_arm64",
        "device_id": "usb:0403:6001",
        "host": {
            "manufacturer": "Test",
            "model": "Host",
            "architecture": "arm64",
            "operating_system": {"family": "windows", "version": "11"},
        },
        "connection_path": [{"kind": "direct_port"}],
        "outcome": "works",
        "evidence": {
            "source_type": "community_report",
            "source_url": "https://example.com/reproduction",
            "source_title": "Reproduction",
        },
        "observed_at": "2025-01-01T00:00:00Z",
        "recorded_at": "2025-01-01T00:00:00Z",
    }


def _support() -> dict:
    return {
        "schema_version": "1.0.0",
        "record_type": "compatibility_support_statement",
        "statement_id": "sup_test_windows",
        "device_id": "usb:0403:6001",
        "scope": {
            "architecture": "any",
            "operating_system": {
                "family": "windows",
                "version_mode": "one_of",
                "versions": ["10", "11"],
            },
            "connection": {"kind": "any_usb"},
        },
        "support_status": "supported",
        "evidence": {
            "source_type": "vendor_documentation",
            "sources": [
                {
                    "source_url": "https://vendor.example/drivers",
                    "source_title": "Drivers",
                }
            ],
            "source_note": "Reviewed vendor support.",
        },
        "reviewed_at": "2026-08-01T00:00:00Z",
        "recorded_at": "2026-08-01T00:00:00Z",
    }


def _freshness_report() -> dict:
    return {
        "as_of": "2026-09-08T00:00:00Z",
        "report_sha256": "a" * 64,
        "evidence": [
            {
                "evidence_kind": "observation",
                "evidence_id": "obs_test_win_arm64",
                "device_id": "usb:0403:6001",
                "age_days": 615,
                "freshness_status": "stale",
            },
            {
                "evidence_kind": "support_statement",
                "evidence_id": "sup_test_windows",
                "device_id": "usb:0403:6001",
                "age_days": 38,
                "freshness_status": "fresh",
            },
        ],
        "sources": [
            {
                "source_url": "https://example.com/reproduction",
                "device_ids": ["usb:0403:6001"],
                "evidence_refs": ["observation:obs_test_win_arm64"],
            },
            {
                "source_url": "https://vendor.example/drivers",
                "device_ids": ["usb:0403:6001"],
                "evidence_refs": ["support_statement:sup_test_windows"],
            },
        ],
    }


def test_operations_report_prioritizes_changes_health_and_stale_evidence() -> None:
    report = evidence_operations.build_operations_report(
        observations=[_observation()],
        support_statements=[_support()],
        freshness_report=_freshness_report(),
        source_check_report={
            "checked_at": "2026-09-08T01:00:00Z",
            "checks": [
                {
                    "source_url": "https://example.com/reproduction",
                    "ok": False,
                    "error": "http_404",
                    "device_ids": ["usb:0403:6001"],
                    "evidence_refs": ["observation:obs_test_win_arm64"],
                },
                {
                    "source_url": "https://vendor.example/drivers",
                    "ok": True,
                    "error": None,
                    "device_ids": ["usb:0403:6001"],
                    "evidence_refs": ["support_statement:sup_test_windows"],
                },
            ],
        },
        vendor_change_report={
            "report_sha256": "b" * 64,
            "changes": [
                {
                    "adapter": "test_vendor",
                    "source_url": "https://vendor.example/drivers",
                    "status": "changed",
                    "changed_fields": ["driver_version"],
                }
            ],
        },
    )

    device = report["devices"]["usb:0403:6001"]
    assert device["platforms"]["observed"] == ["windows/arm64"]
    assert device["platforms"]["vendor_supported"] == ["windows/arm64", "windows/x86_64"]
    assert device["platforms"]["corroborated"] == ["windows/arm64"]
    assert device["platforms"]["vendor_only"] == ["windows/x86_64"]
    assert device["freshness"] == {"fresh": 1, "aging": 0, "stale": 1}

    assert report["work_queue"][0]["task_type"] == "vendor_semantic_change"
    assert report["work_queue"][0]["priority"] == "P0"
    assert {item["task_type"] for item in report["work_queue"]} == {
        "vendor_semantic_change",
        "source_health",
        "stale_evidence",
        "reproduction_gap",
    }
    assert report["summary"]["vendor_only_platform_cells"] == 1
    assert "Prioritized work queue" in evidence_operations.render_markdown(report)


def test_operations_report_is_deterministic() -> None:
    kwargs = {
        "observations": [_observation()],
        "support_statements": [_support()],
        "freshness_report": _freshness_report(),
        "source_check_report": {
            "checked_at": "2026-09-08T01:00:00Z",
            "checks": [],
        },
        "vendor_change_report": {"report_sha256": "b" * 64, "changes": []},
    }

    first = evidence_operations.build_operations_report(**kwargs)
    second = evidence_operations.build_operations_report(**kwargs)
    assert first == second
    assert first["report_sha256"] == second["report_sha256"]
