import json
from pathlib import Path

import compatforge_pipeline.diagnostics as diagnostics
from compatforge_pipeline.contracts import validate_document
from compatforge_pipeline.diagnostics import (
    _collect_linux_target,
    _parse_macos_usb_payload,
    _parse_windows_usb_payload,
    collect_diagnostic,
    normalize_architecture,
    parse_usb_device_id,
)


def test_normalize_architecture() -> None:
    assert normalize_architecture("AMD64") == "x86_64"
    assert normalize_architecture("aarch64") == "arm64"
    assert normalize_architecture("mips64") == "unknown"


def test_parse_usb_device_id_canonicalizes() -> None:
    assert parse_usb_device_id("usb:403:6001") == ("usb:0403:6001", "0403", "6001")


def test_windows_parser_emits_only_safe_allowlisted_fields() -> None:
    payload = {
        "devices": [
            {
                "vendor_id": "0403",
                "product_id": "6001",
                "status": "OK",
                "serial_number": "DO-NOT-LEAK",
                "instance_id": "USB\\VID_0403&PID_6001\\DO-NOT-LEAK",
            }
        ]
    }
    matches, count = _parse_windows_usb_payload(payload, "usb:0403:6001")
    assert count == 1
    assert matches == [
        {
            "device_id": "usb:0403:6001",
            "connection_path": "unspecified",
            "status": "OK",
        }
    ]
    assert "DO-NOT-LEAK" not in json.dumps(matches)


def test_macos_parser_drops_serial_and_unrelated_devices() -> None:
    payload = {
        "SPUSBDataType": [
            {
                "_name": "Target",
                "vendor_id": "0x0403 (FTDI)",
                "product_id": "0x6001",
                "serial_num": "DO-NOT-LEAK",
            },
            {
                "_name": "Other",
                "vendor_id": "0x1234",
                "product_id": "0x5678",
            },
        ]
    }
    matches, count = _parse_macos_usb_payload(payload, "usb:0403:6001")
    assert count == 1
    assert matches == [{"device_id": "usb:0403:6001", "connection_path": "unspecified"}]
    assert "DO-NOT-LEAK" not in json.dumps(matches)
    assert "1234" not in json.dumps(matches)


def test_linux_collector_reads_safe_target_fields_only(tmp_path: Path) -> None:
    target = tmp_path / "1-2.3"
    target.mkdir()
    (target / "idVendor").write_text("0403\n", encoding="utf-8")
    (target / "idProduct").write_text("6001\n", encoding="utf-8")
    (target / "speed").write_text("480\n", encoding="utf-8")
    (target / "serial").write_text("DO-NOT-LEAK\n", encoding="utf-8")

    other = tmp_path / "1-4"
    other.mkdir()
    (other / "idVendor").write_text("1234\n", encoding="utf-8")
    (other / "idProduct").write_text("5678\n", encoding="utf-8")
    (other / "serial").write_text("OTHER-SECRET\n", encoding="utf-8")

    matches, count = _collect_linux_target("0403", "6001", sysfs_root=tmp_path)
    assert count == 1
    assert matches == [
        {
            "device_id": "usb:0403:6001",
            "connection_path": "usb_hub",
            "status": "present",
            "speed_mbps": 480.0,
        }
    ]
    rendered = json.dumps(matches)
    assert "DO-NOT-LEAK" not in rendered
    assert "OTHER-SECRET" not in rendered


def test_collect_diagnostic_validates_and_never_uploads(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostics,
        "_collect_platform_host",
        lambda system_name=None: (
            {
                "os_family": "windows",
                "os_name": "Windows 11",
                "os_version": "11",
                "os_build": "26100",
                "architecture": "arm64",
            },
            {"manufacturer": "Synthetic", "model": "Test Host"},
            [],
        ),
    )
    monkeypatch.setattr(
        diagnostics,
        "_collect_target",
        lambda system_name, vid, pid: (
            [{"device_id": "usb:0403:6001", "connection_path": "unspecified"}],
            1,
        ),
    )

    manifest = collect_diagnostic(
        "usb:0403:6001",
        system_name="Windows",
        generated_at="2026-09-07T00:00:00Z",
    )
    validate_document(manifest)
    assert manifest["target"]["present"] is True
    assert manifest["privacy"]["automatic_upload"] is False
    assert manifest["privacy"]["unrelated_usb_devices_in_manifest"] is False
