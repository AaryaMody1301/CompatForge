"""Ingest and export deterministic CompatForge compatibility evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import duckdb

from .resolver import load_observations, load_support_statements

EVIDENCE_MANIFEST_VERSION = 1
EVIDENCE_SNAPSHOT_VERSION = 1


def _canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _observation_row(record: dict[str, Any]) -> tuple[Any, ...]:
    host = record["host"]
    operating_system = host["operating_system"]
    driver = record.get("driver") or {}
    software = record.get("software") or {}
    connection_path = record["connection_path"]
    evidence = record["evidence"]
    return (
        record["observation_id"],
        record["device_id"],
        host["manufacturer"],
        host["model"],
        host["architecture"],
        operating_system["family"],
        operating_system["version"],
        operating_system.get("build"),
        _json_text(connection_path),
        ">".join(item["kind"] for item in connection_path),
        driver.get("name"),
        driver.get("version"),
        record.get("firmware_version"),
        software.get("name"),
        software.get("version"),
        record["outcome"],
        _json_text(record.get("conditions", [])),
        evidence["source_type"],
        evidence["source_url"],
        evidence["source_title"],
        record["observed_at"],
        record["recorded_at"],
        _json_text(record.get("limitations", [])),
        record.get("notes"),
        _canonical_sha256(record),
    )


def _support_row(record: dict[str, Any]) -> tuple[Any, ...]:
    scope = record["scope"]
    operating_system = scope["operating_system"]
    connection = scope["connection"]
    driver = record.get("driver") or {}
    software = record.get("software") or {}
    evidence = record["evidence"]
    return (
        record["statement_id"],
        record["device_id"],
        scope["architecture"],
        operating_system["family"],
        operating_system["version_mode"],
        _json_text(operating_system.get("versions", [])),
        operating_system.get("minimum_version"),
        connection["kind"],
        connection.get("minimum_usb_generation"),
        driver.get("name"),
        driver.get("version"),
        software.get("name"),
        software.get("version"),
        record["support_status"],
        _json_text(record.get("conditions", [])),
        evidence["source_type"],
        _json_text(evidence["sources"]),
        evidence["source_note"],
        record["reviewed_at"],
        record["recorded_at"],
        _json_text(record.get("limitations", [])),
        _canonical_sha256(record),
    )


def ingest_evidence(
    *,
    workspace: Path,
    observation_paths: list[Path],
    support_paths: list[Path],
    as_of: str,
) -> dict[str, Any]:
    """Load validated evidence records into Bronze DuckDB tables."""
    workspace = workspace.resolve()
    database_path = workspace / "compatforge.duckdb"
    if not database_path.exists():
        raise FileNotFoundError(f"Identity DuckDB does not exist: {database_path}")

    observations = load_observations(observation_paths)
    support_statements = load_support_statements(support_paths)
    bronze_dir = workspace / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    observations_parquet = bronze_dir / "compatibility_observations.parquet"
    support_parquet = bronze_dir / "support_statements.parquet"

    with duckdb.connect(str(database_path)) as connection:
        connection.execute("CREATE SCHEMA IF NOT EXISTS bronze")
        connection.execute(
            """
            CREATE OR REPLACE TABLE bronze.evidence_run_metadata (
                as_of VARCHAR NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO bronze.evidence_run_metadata VALUES (?)", [as_of])
        connection.execute(
            """
            CREATE OR REPLACE TABLE bronze.compatibility_observations (
                observation_id VARCHAR NOT NULL,
                device_id VARCHAR NOT NULL,
                host_manufacturer VARCHAR NOT NULL,
                host_model VARCHAR NOT NULL,
                architecture VARCHAR NOT NULL,
                os_family VARCHAR NOT NULL,
                os_version VARCHAR NOT NULL,
                os_build VARCHAR,
                connection_path_json VARCHAR NOT NULL,
                connection_signature VARCHAR NOT NULL,
                driver_name VARCHAR,
                driver_version VARCHAR,
                firmware_version VARCHAR,
                software_name VARCHAR,
                software_version VARCHAR,
                outcome VARCHAR NOT NULL,
                conditions_json VARCHAR NOT NULL,
                evidence_source_type VARCHAR NOT NULL,
                source_url VARCHAR NOT NULL,
                source_title VARCHAR NOT NULL,
                observed_at VARCHAR NOT NULL,
                recorded_at VARCHAR NOT NULL,
                limitations_json VARCHAR NOT NULL,
                notes VARCHAR,
                record_sha256 VARCHAR NOT NULL
            )
            """
        )
        observation_rows = [_observation_row(item) for item in observations]
        if observation_rows:
            observation_insert = (
                "INSERT INTO bronze.compatibility_observations VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            )
            connection.executemany(observation_insert, observation_rows)
        connection.execute(
            """
            CREATE OR REPLACE TABLE bronze.support_statements (
                statement_id VARCHAR NOT NULL,
                device_id VARCHAR NOT NULL,
                architecture VARCHAR NOT NULL,
                os_family VARCHAR NOT NULL,
                version_mode VARCHAR NOT NULL,
                versions_json VARCHAR NOT NULL,
                minimum_version VARCHAR,
                connection_kind VARCHAR NOT NULL,
                minimum_usb_generation VARCHAR,
                driver_name VARCHAR,
                driver_version VARCHAR,
                software_name VARCHAR,
                software_version VARCHAR,
                support_status VARCHAR NOT NULL,
                conditions_json VARCHAR NOT NULL,
                evidence_source_type VARCHAR NOT NULL,
                sources_json VARCHAR NOT NULL,
                source_note VARCHAR NOT NULL,
                reviewed_at VARCHAR NOT NULL,
                recorded_at VARCHAR NOT NULL,
                limitations_json VARCHAR NOT NULL,
                record_sha256 VARCHAR NOT NULL
            )
            """
        )
        support_rows = [_support_row(item) for item in support_statements]
        if support_rows:
            support_insert = (
                "INSERT INTO bronze.support_statements VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            )
            connection.executemany(support_insert, support_rows)

        observations_copy = (
            "COPY (SELECT * FROM bronze.compatibility_observations ORDER BY observation_id) "
            f"TO '{_sql_path(observations_parquet)}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        support_copy = (
            "COPY (SELECT * FROM bronze.support_statements ORDER BY statement_id) "
            f"TO '{_sql_path(support_parquet)}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        connection.execute(observations_copy)
        connection.execute(support_copy)

    observation_manifest = sorted(
        (
            {"id": item["observation_id"], "sha256": _canonical_sha256(item)}
            for item in observations
        ),
        key=lambda item: item["id"],
    )
    support_manifest = sorted(
        (
            {"id": item["statement_id"], "sha256": _canonical_sha256(item)}
            for item in support_statements
        ),
        key=lambda item: item["id"],
    )
    manifest = {
        "manifest_version": EVIDENCE_MANIFEST_VERSION,
        "as_of": as_of,
        "counts": {
            "observations": len(observations),
            "support_statements": len(support_statements),
        },
        "records": {
            "observations": observation_manifest,
            "support_statements": support_manifest,
        },
        "artifacts": {
            "observations_parquet": str(observations_parquet.relative_to(workspace)),
            "support_parquet": str(support_parquet.relative_to(workspace)),
        },
    }
    manifest["input_sha256"] = _canonical_sha256(
        {"as_of": as_of, "records": manifest["records"]}
    )
    _write_json(workspace / "manifests" / "evidence_manifest.json", manifest)
    return manifest


def _export_relation(
    connection: duckdb.DuckDBPyConnection,
    *,
    query: str,
    jsonl_path: Path,
    parquet_path: Path,
) -> int:
    rows = connection.execute(query).fetchall()
    columns = [item[0] for item in connection.description]
    connection.execute(
        f"COPY ({query}) TO '{_sql_path(parquet_path)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            record = dict(zip(columns, row, strict=True))
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return len(rows)


def export_evidence_snapshot(*, workspace: Path) -> dict[str, Any]:
    """Export dbt-built evidence facts and coverage as deterministic public artifacts."""
    workspace = workspace.resolve()
    database_path = workspace / "compatforge.duckdb"
    evidence_manifest_path = workspace / "manifests" / "evidence_manifest.json"
    evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))

    public_dir = workspace / "public" / "evidence"
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(parents=True)

    relations = {
        "compatibility_observations": (
            "SELECT * FROM analytics.fact_compatibility_observations ORDER BY observation_id"
        ),
        "support_statements": (
            "SELECT * FROM analytics.fact_support_statements ORDER BY statement_id"
        ),
        "evidence_coverage": "SELECT * FROM analytics.evidence_coverage ORDER BY device_id",
    }
    counts: dict[str, int] = {}
    files: dict[str, str] = {}
    with duckdb.connect(str(database_path), read_only=True) as connection:
        for name, query in relations.items():
            jsonl_path = public_dir / f"{name}.jsonl"
            parquet_path = public_dir / f"{name}.parquet"
            counts[name] = _export_relation(
                connection,
                query=query,
                jsonl_path=jsonl_path,
                parquet_path=parquet_path,
            )
            files[jsonl_path.name] = _sha256_file(jsonl_path)
            files[parquet_path.name] = _sha256_file(parquet_path)

    snapshot = {
        "schema_version": EVIDENCE_SNAPSHOT_VERSION,
        "as_of": evidence_manifest["as_of"],
        "input_sha256": evidence_manifest["input_sha256"],
        "counts": counts,
        "files": dict(sorted(files.items())),
    }
    snapshot["snapshot_sha256"] = _canonical_sha256(snapshot)
    _write_json(public_dir / "snapshot_manifest.json", snapshot)
    return snapshot


def verify_snapshots(first: Path, second: Path) -> None:
    """Fail when two evidence snapshot manifests differ."""
    first_payload = json.loads(first.read_text(encoding="utf-8"))
    second_payload = json.loads(second.read_text(encoding="utf-8"))
    if first_payload != second_payload:
        raise ValueError("Evidence snapshots are not deterministic")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Ingest validated evidence into DuckDB")
    ingest.add_argument("--workspace", type=Path, required=True)
    ingest.add_argument("--observations", nargs="*", type=Path, default=[])
    ingest.add_argument("--support", nargs="*", type=Path, default=[])
    ingest.add_argument("--as-of", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Export deterministic evidence marts")
    snapshot.add_argument("--workspace", type=Path, required=True)

    verify = subparsers.add_parser("verify", help="Compare two evidence snapshot manifests")
    verify.add_argument("first", type=Path)
    verify.add_argument("second", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "ingest":
        ingest_evidence(
            workspace=args.workspace,
            observation_paths=args.observations,
            support_paths=args.support,
            as_of=args.as_of,
        )
        return 0
    if args.command == "snapshot":
        export_evidence_snapshot(workspace=args.workspace)
        return 0
    if args.command == "verify":
        verify_snapshots(args.first, args.second)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
