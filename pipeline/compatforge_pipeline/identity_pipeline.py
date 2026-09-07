"""Build deterministic USB hardware identity snapshots with DuckDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from compatforge_pipeline.usb_ids import (
    USB_IDS_HOMEPAGE,
    USB_IDS_LICENSE,
    USB_IDS_PARSER_VERSION,
    download_usb_ids,
    load_usb_ids,
    parse_usb_ids,
    source_sha256,
)

MANIFEST_VERSION = 1
SNAPSHOT_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def build_bronze(
    *,
    workspace: Path,
    input_path: Path | None = None,
    retrieved_at: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    """Create raw/bronze artifacts and a DuckDB database from one usb.ids snapshot."""
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    downloaded = download_usb_ids() if input_path is None else load_usb_ids(input_path)

    content = downloaded.content
    vendors, devices = parse_usb_ids(content)
    digest = source_sha256(content)
    effective_source_url = source_url or downloaded.source_url
    retrieved_at = retrieved_at or _utc_now()

    raw_dir = workspace / "raw" / "usb_ids"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{digest}.usb.ids"
    raw_path.write_bytes(content)

    bronze_dir = workspace / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    vendors_parquet = bronze_dir / "usb_vendors.parquet"
    devices_parquet = bronze_dir / "usb_devices.parquet"

    database_path = workspace / "compatforge.duckdb"
    database_path.unlink(missing_ok=True)
    Path(f"{database_path}.wal").unlink(missing_ok=True)

    with duckdb.connect(str(database_path)) as connection:
        connection.execute("CREATE SCHEMA bronze")
        connection.execute(
            """
            CREATE TABLE bronze.usb_vendors (
                vendor_id VARCHAR NOT NULL,
                vendor_name VARCHAR NOT NULL,
                source_line BIGINT NOT NULL,
                source_sha256 VARCHAR NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE bronze.usb_devices (
                device_id VARCHAR NOT NULL,
                vendor_id VARCHAR NOT NULL,
                product_id VARCHAR NOT NULL,
                product_name VARCHAR NOT NULL,
                source_line BIGINT NOT NULL,
                source_sha256 VARCHAR NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO bronze.usb_vendors VALUES (?, ?, ?, ?)",
            [(row.vendor_id, row.vendor_name, row.source_line, digest) for row in vendors],
        )
        connection.executemany(
            "INSERT INTO bronze.usb_devices VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    row.device_id,
                    row.vendor_id,
                    row.product_id,
                    row.product_name,
                    row.source_line,
                    digest,
                )
                for row in devices
            ],
        )
        connection.execute(
            f"COPY (SELECT * FROM bronze.usb_vendors ORDER BY vendor_id) "
            f"TO '{_sql_path(vendors_parquet)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        connection.execute(
            f"COPY (SELECT * FROM bronze.usb_devices ORDER BY device_id) "
            f"TO '{_sql_path(devices_parquet)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "source": {
            "name": "usb.ids",
            "homepage": USB_IDS_HOMEPAGE,
            "source_url": effective_source_url,
            "license": USB_IDS_LICENSE,
            "parser_version": USB_IDS_PARSER_VERSION,
            "retrieved_at": retrieved_at,
            "upstream_last_modified": downloaded.upstream_last_modified,
            "upstream_etag": downloaded.upstream_etag,
            "sha256": digest,
        },
        "counts": {"vendors": len(vendors), "devices": len(devices)},
        "artifacts": {
            "raw": str(raw_path.relative_to(workspace)),
            "vendors_parquet": str(vendors_parquet.relative_to(workspace)),
            "devices_parquet": str(devices_parquet.relative_to(workspace)),
            "duckdb": database_path.name,
        },
    }
    _write_json(workspace / "manifests" / "source_manifest.json", manifest)
    return manifest


def export_public_snapshot(*, workspace: Path) -> dict[str, Any]:
    """Export the dbt-built device catalog to deterministic public artifacts."""
    workspace = workspace.resolve()
    database_path = workspace / "compatforge.duckdb"
    source_manifest_path = workspace / "manifests" / "source_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))

    public_dir = workspace / "public"
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(parents=True)
    jsonl_path = public_dir / "device_catalog.jsonl"
    parquet_path = public_dir / "device_catalog.parquet"

    query = """
        SELECT
            device_id,
            vendor_id,
            vendor_name,
            product_id,
            product_name,
            interface_type,
            identity_source,
            source_sha256
        FROM analytics.device_catalog
        ORDER BY device_id
    """
    with duckdb.connect(str(database_path), read_only=True) as connection:
        rows = connection.execute(query).fetchall()
        columns = [item[0] for item in connection.description]
        connection.execute(
            f"COPY ({query}) TO '{_sql_path(parquet_path)}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            record = dict(zip(columns, row, strict=True))
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "source_sha256": source_manifest["source"]["sha256"],
        "row_count": len(rows),
        "files": {
            "device_catalog.jsonl": _sha256_file(jsonl_path),
            "device_catalog.parquet": _sha256_file(parquet_path),
        },
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical).hexdigest()
    _write_json(public_dir / "snapshot_manifest.json", snapshot)
    return snapshot


def verify_snapshots(first: Path, second: Path) -> None:
    """Fail when two snapshot manifests do not describe identical outputs."""
    first_payload = json.loads(first.read_text(encoding="utf-8"))
    second_payload = json.loads(second.read_text(encoding="utf-8"))
    if first_payload != second_payload:
        raise ValueError("Identity snapshots are not deterministic")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bronze = subparsers.add_parser("bronze", help="Build raw and bronze identity artifacts")
    bronze.add_argument("--workspace", type=Path, required=True)
    bronze.add_argument("--input", dest="input_path", type=Path)
    bronze.add_argument("--retrieved-at")
    bronze.add_argument("--source-url")

    snapshot = subparsers.add_parser("snapshot", help="Export the dbt-built public catalog")
    snapshot.add_argument("--workspace", type=Path, required=True)

    verify = subparsers.add_parser("verify", help="Compare two snapshot manifests")
    verify.add_argument("first", type=Path)
    verify.add_argument("second", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "bronze":
        build_bronze(
            workspace=args.workspace,
            input_path=args.input_path,
            retrieved_at=args.retrieved_at,
            source_url=args.source_url,
        )
        return 0
    if args.command == "snapshot":
        export_public_snapshot(workspace=args.workspace)
        return 0
    if args.command == "verify":
        verify_snapshots(args.first, args.second)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
