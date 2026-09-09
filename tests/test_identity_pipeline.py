from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from compatforge_pipeline.identity_pipeline import build_bronze, export_public_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "usb.ids"
FIXED_RETRIEVED_AT = "2026-01-01T00:00:00Z"


def test_bronze_build_is_provenance_complete(tmp_path: Path) -> None:
    manifest = build_bronze(
        workspace=tmp_path,
        input_path=FIXTURE,
        retrieved_at=FIXED_RETRIEVED_AT,
        source_url="synthetic://tests/fixtures/usb.ids",
    )
    assert manifest["counts"] == {"vendors": 2, "devices": 3}
    assert len(manifest["source"]["sha256"]) == 64
    assert (tmp_path / manifest["artifacts"]["raw"]).exists()
    assert (tmp_path / manifest["artifacts"]["vendors_parquet"]).exists()
    assert (tmp_path / manifest["artifacts"]["devices_parquet"]).exists()


def test_bronze_build_accepts_legacy_latin1_usb_ids(tmp_path: Path) -> None:
    source = tmp_path / "legacy.usb.ids"
    source.write_bytes("1234  Caf\u00e9 Devices\n\t0001  Serial Adapter\n".encode("iso-8859-1"))
    workspace = tmp_path / "workspace"

    manifest = build_bronze(
        workspace=workspace,
        input_path=source,
        retrieved_at=FIXED_RETRIEVED_AT,
        source_url="synthetic://legacy-usb.ids",
    )

    assert manifest["counts"] == {"vendors": 1, "devices": 1}
    assert manifest["source"]["parser_version"] == "2"


def test_public_snapshot_contains_identity_only(tmp_path: Path) -> None:
    import duckdb

    build_bronze(
        workspace=tmp_path,
        input_path=FIXTURE,
        retrieved_at=FIXED_RETRIEVED_AT,
        source_url="synthetic://tests/fixtures/usb.ids",
    )
    database = tmp_path / "compatforge.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE SCHEMA analytics")
        connection.execute(
            """
            CREATE TABLE analytics.device_catalog AS
            SELECT
                d.device_id,
                d.vendor_id,
                v.vendor_name,
                d.product_id,
                d.product_name,
                'usb' AS interface_type,
                'usb.ids' AS identity_source,
                d.source_sha256
            FROM bronze.usb_devices d
            JOIN bronze.usb_vendors v USING (vendor_id)
            """
        )

    manifest = export_public_snapshot(workspace=tmp_path)
    catalog = (tmp_path / "public" / "device_catalog.jsonl").read_text(encoding="utf-8")
    assert manifest["row_count"] == 3
    assert "compatibility" not in catalog.lower()
    assert "usb:1234:0001" in catalog
