import json
from pathlib import Path

import pytest

from compatforge_pipeline import vendor_adapters

CHECKED_AT = "2026-09-08T07:10:00Z"

FTDI_HTML = """
<html><body>
<p>The Windows driver installer is not available for ARM64.</p>
<table>
<tr><td>Windows (Desktop)*</td><td>2025-03-04</td><td>2.12.36.20</td>
<td>2.12.36.20</td><td>2.12.36.20A</td><td>WHQL Certified</td></tr>
<tr><td>Windows (Universal)***</td><td>2025-03-04</td><td>2.12.36.20U</td>
<td>2.12.36.20U</td><td>2.12.36.20UA</td></tr>
</table>
</body></html>
"""

SALEAE_HTML = """
<html><body>
<h1>Supported Operating Systems</h1>
<ul>
<li>Windows 10 &amp; 11 (x64)</li>
<li>macOS 12 Monterey+ (Intel / Apple silicon)</li>
<li>Ubuntu 20.04+ (64-bit), et al.</li>
</ul>
</body></html>
"""


def test_ftdi_adapter_extracts_reviewed_semantics() -> None:
    snapshot = vendor_adapters.snapshot_from_html(
        "ftdi_vcp",
        FTDI_HTML,
        checked_at=CHECKED_AT,
    )

    assert snapshot["facts"] == {
        "installer_arm64_note": True,
        "windows_desktop_arm64_version": "2.12.36.20A",
        "windows_desktop_release_date": "2025-03-04",
        "windows_desktop_x64_version": "2.12.36.20",
        "windows_universal_arm64_version": "2.12.36.20UA",
    }
    assert snapshot["semantic_sha256"] == (
        "8574c5810f1defd56a005b8b9a642078234ed25e1a9485ccee7c8c70b618da0c"
    )


def test_saleae_adapter_extracts_reviewed_semantics() -> None:
    snapshot = vendor_adapters.snapshot_from_html(
        "saleae_supported_os",
        SALEAE_HTML,
        checked_at=CHECKED_AT,
    )

    assert snapshot["facts"] == {
        "macos_apple_silicon_declared": True,
        "ubuntu_64_bit_declared": True,
        "windows_architectures": ["x64"],
        "windows_versions": ["10", "11"],
    }
    assert snapshot["semantic_sha256"] == (
        "5f5091a744f81dfcf56d96ac01532f1c3592d39b25c25e777521dfe301b17806"
    )


def test_change_report_surfaces_semantic_delta(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baselines"
    baseline_dir.mkdir()
    baseline = vendor_adapters.snapshot_from_html(
        "ftdi_vcp",
        FTDI_HTML,
        checked_at=CHECKED_AT,
    )
    (baseline_dir / "ftdi_vcp.json").write_text(
        json.dumps(
            {
                "adapter": baseline["adapter"],
                "source_url": baseline["source_url"],
                "facts": baseline["facts"],
                "semantic_sha256": baseline["semantic_sha256"],
            }
        ),
        encoding="utf-8",
    )

    changed_html = FTDI_HTML.replace("2.12.36.20A", "2.12.36.21A")
    changed = vendor_adapters.snapshot_from_html(
        "ftdi_vcp",
        changed_html,
        checked_at=CHECKED_AT,
    )
    report = vendor_adapters.build_change_report(
        snapshot={
            "report_version": 1,
            "checked_at": CHECKED_AT,
            "sources": [changed],
        },
        baseline_dir=baseline_dir,
    )

    assert report["summary"] == {
        "total": 1,
        "unchanged": 0,
        "changed": 1,
        "missing_baseline": 0,
    }
    assert report["changes"][0]["changed_fields"] == ["windows_desktop_arm64_version"]
    assert "review candidate only" in vendor_adapters.render_change_markdown(report)


def test_change_report_is_unchanged_for_same_semantics(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baselines"
    baseline_dir.mkdir()
    current = vendor_adapters.snapshot_from_html(
        "saleae_supported_os",
        SALEAE_HTML,
        checked_at=CHECKED_AT,
    )
    (baseline_dir / "saleae_supported_os.json").write_text(
        json.dumps(
            {
                "adapter": current["adapter"],
                "source_url": current["source_url"],
                "facts": current["facts"],
                "semantic_sha256": current["semantic_sha256"],
            }
        ),
        encoding="utf-8",
    )

    report = vendor_adapters.build_change_report(
        snapshot={
            "report_version": 1,
            "checked_at": CHECKED_AT,
            "sources": [current],
        },
        baseline_dir=baseline_dir,
    )

    assert report["summary"]["unchanged"] == 1
    assert report["changes"][0]["changed_fields"] == []


def test_adapter_rejects_redirect_outside_permitted_host() -> None:
    with pytest.raises(ValueError, match="outside permitted host"):
        vendor_adapters.snapshot_from_html(
            "ftdi_vcp",
            FTDI_HTML,
            checked_at=CHECKED_AT,
            final_url="https://example.com/drivers/vcp-drivers/",
        )


def test_ftdi_adapter_fails_closed_when_required_fact_disappears() -> None:
    with pytest.raises(ValueError, match="ARM64 installer limitation"):
        vendor_adapters.snapshot_from_html(
            "ftdi_vcp",
            FTDI_HTML.replace(
                "The Windows driver installer is not available for ARM64.",
                "Installer information is available below.",
            ),
            checked_at=CHECKED_AT,
        )
