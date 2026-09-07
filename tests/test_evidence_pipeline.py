from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from compatforge_pipeline.evidence_pipeline import ingest_evidence
from compatforge_pipeline.identity_pipeline import build_bronze

USB_FIXTURE = Path(__file__).parent / "fixtures" / "usb.ids"
EVIDENCE_FIXTURE = Path(__file__).parent / "fixtures" / "evidence"
AS_OF = "2026-09-07T00:00:00Z"


def _build_workspace(path: Path) -> None:
    build_bronze(
        workspace=path,
        input_path=USB_FIXTURE,
        retrieved_at="2026-01-01T00:00:00Z",
        source_url="synthetic://tests/fixtures/usb.ids",
    )


def test_evidence_ingest_is_manifest_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _build_workspace(first)
    _build_workspace(second)

    first_manifest = ingest_evidence(
        workspace=first,
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of=AS_OF,
    )
    second_manifest = ingest_evidence(
        workspace=second,
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of=AS_OF,
    )

    assert first_manifest == second_manifest
    assert first_manifest["counts"] == {"observations": 1, "support_statements": 1}
    assert len(first_manifest["input_sha256"]) == 64


def test_evidence_ingest_creates_bronze_tables(tmp_path: Path) -> None:
    import duckdb

    _build_workspace(tmp_path)
    ingest_evidence(
        workspace=tmp_path,
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of=AS_OF,
    )

    with duckdb.connect(str(tmp_path / "compatforge.duckdb"), read_only=True) as connection:
        observation_count = connection.execute(
            "SELECT count(*) FROM bronze.compatibility_observations"
        ).fetchone()[0]
        support_count = connection.execute(
            "SELECT count(*) FROM bronze.support_statements"
        ).fetchone()[0]
        as_of = connection.execute("SELECT as_of FROM bronze.evidence_run_metadata").fetchone()[0]

    assert observation_count == 1
    assert support_count == 1
    assert as_of == AS_OF
