from __future__ import annotations

import json
from pathlib import Path

from compatforge_pipeline.cli import main


FIXTURE = Path("data/fixtures/diagnostic_manifest.json")


def test_unified_cli_reports_release_version(capsys) -> None:
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "0.3.0rc1" in capsys.readouterr().out


def test_unified_cli_prepares_approved_local_handoff(tmp_path: Path) -> None:
    explanation_path = tmp_path / "explanation.json"
    handoff_path = tmp_path / "handoff.json"

    assert (
        main(
            [
                "explain",
                "--diagnostic",
                str(FIXTURE),
                "--output",
                str(explanation_path),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "prepare-contribution",
                "--diagnostic",
                str(FIXTURE),
                "--explanation",
                str(explanation_path),
                "--approve-export",
                "--output",
                str(handoff_path),
            ]
        )
        == 0
    )

    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert handoff["record_type"] == "contribution_handoff"
    assert handoff["evidence_ready"] is False
    assert handoff["privacy"]["automatic_upload"] is False
    assert handoff["privacy"]["network_request_performed"] is False


def test_unified_cli_refuses_unapproved_handoff(tmp_path: Path) -> None:
    explanation_path = tmp_path / "explanation.json"
    assert (
        main(
            [
                "explain",
                "--diagnostic",
                str(FIXTURE),
                "--output",
                str(explanation_path),
            ]
        )
        == 0
    )

    assert (
        main(
            [
                "prepare-contribution",
                "--diagnostic",
                str(FIXTURE),
                "--explanation",
                str(explanation_path),
                "--output",
                str(tmp_path / "handoff.json"),
            ]
        )
        == 1
    )
