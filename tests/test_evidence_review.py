from pathlib import Path

import pytest

from compatforge_pipeline import evidence_review

EVIDENCE_FIXTURE = Path(__file__).parent / "fixtures" / "evidence"
AS_OF = "2026-09-07T00:00:00Z"


@pytest.mark.parametrize(
    ("age_days", "expected"),
    [
        (0, "fresh"),
        (180, "fresh"),
        (181, "aging"),
        (365, "aging"),
        (366, "stale"),
    ],
)
def test_classify_freshness_matches_data_platform(age_days: int, expected: str) -> None:
    assert evidence_review.classify_freshness(age_days) == expected


def test_freshness_report_is_deterministic() -> None:
    first = evidence_review.build_freshness_report(
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of=AS_OF,
    )
    second = evidence_review.build_freshness_report(
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of=AS_OF,
    )

    assert first == second
    assert first["summary"] == {
        "total": 2,
        "fresh": 2,
        "aging": 0,
        "stale": 0,
        "observations": 1,
        "support_statements": 1,
    }
    assert first["devices"]["usb:1234:0001"]["total"] == 2
    assert len(first["sources"]) == 2
    assert len(first["report_sha256"]) == 64


def test_report_surfaces_stale_records_without_rewriting_them() -> None:
    report = evidence_review.build_freshness_report(
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of="2027-06-03T00:00:00Z",
    )

    assert report["summary"]["stale"] == 2
    assert report["review_queue"]["stale"] == [
        "obs_example_debug_win11",
        "sup_example_debug_win11",
    ]
    assert "review input only" in evidence_review.render_markdown(report)


def test_future_dated_evidence_fails_review() -> None:
    with pytest.raises(ValueError, match="future-dated"):
        evidence_review.build_freshness_report(
            observation_paths=[EVIDENCE_FIXTURE / "observations"],
            support_paths=[EVIDENCE_FIXTURE / "support"],
            as_of="2026-05-01T00:00:00Z",
        )


def test_source_check_report_keeps_evidence_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = evidence_review.build_freshness_report(
        observation_paths=[EVIDENCE_FIXTURE / "observations"],
        support_paths=[EVIDENCE_FIXTURE / "support"],
        as_of=AS_OF,
    )

    monkeypatch.setattr(
        evidence_review,
        "check_source",
        lambda url, timeout_seconds: {
            "ok": True,
            "status_code": 200,
            "final_url": url,
            "etag": '"test"',
            "last_modified": None,
            "error": None,
        },
    )

    checks = evidence_review.build_source_check_report(
        freshness_report=report,
        checked_at="2026-09-07T12:00:00Z",
        timeout_seconds=1.0,
    )

    assert checks["summary"] == {"total": 2, "reachable": 2, "unreachable": 0}
    assert all(item["evidence_refs"] for item in checks["checks"])
    assert checks["freshness_report_sha256"] == report["report_sha256"]
