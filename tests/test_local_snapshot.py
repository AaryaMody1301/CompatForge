from pathlib import Path

from compatforge_pipeline.local_snapshot import (
    build_snapshot,
    load_packaged_snapshot,
    snapshot_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_packaged_snapshot_matches_reviewed_evidence() -> None:
    expected = build_snapshot(
        [REPO_ROOT / "data/evidence/observations"],
        [REPO_ROOT / "data/evidence/vendor"],
    )
    packaged = load_packaged_snapshot()
    assert packaged == expected
    assert packaged["observation_count"] == 1
    assert packaged["support_statement_count"] == 5
    assert len(snapshot_sha256(packaged)) == 64


def test_packaged_snapshot_has_expected_reviewed_ids() -> None:
    snapshot = load_packaged_snapshot()
    assert [item["observation_id"] for item in snapshot["observations"]] == [
        "obs_avrdude_ft232r_win11arm64"
    ]
    assert [item["statement_id"] for item in snapshot["support_statements"]] == [
        "sup_ftdi_ft232r_win11_arm64",
        "sup_saleae_lp8_macos_arm64",
        "sup_saleae_lp8_macos_x64",
        "sup_saleae_lp8_windows_arm64",
        "sup_saleae_lp8_windows_x64",
    ]
