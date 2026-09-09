from __future__ import annotations

import pytest
from compatforge_pipeline.release_acceptance import (
    ReleaseAcceptanceError,
    evaluate_acceptance,
)

COMMIT = "a" * 40
TAG = "v1.0.0-rc.1"
BRANCH_RULESET = {
    "name": "main protection",
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
}
TAG_RULESET = {
    "name": "release tag protection",
    "target": "tag",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
}


def _report(
    *,
    protected: bool = True,
    rulesets: list[dict] | None = None,
    releases: list[dict] | None = None,
    immutable: bool = True,
    production_commit: str = COMMIT,
) -> dict:
    return evaluate_acceptance(
        expected_commit=COMMIT,
        release_tag=TAG,
        branch={"commit": {"sha": COMMIT}, "protected": protected},
        rulesets=[BRANCH_RULESET, TAG_RULESET] if rulesets is None else rulesets,
        releases=[] if releases is None else releases,
        immutable_releases={"enabled": immutable, "enforced_by_owner": False},
        production_headers={"x-compatforge-commit": production_commit},
    )


def _check(report: dict, name: str) -> dict:
    return next(item for item in report["checks"] if item["name"] == name)


def test_release_acceptance_passes_only_when_all_external_gates_match() -> None:
    report = _report()
    assert report["passed"] is True
    assert all(item["passed"] for item in report["checks"])


def test_release_acceptance_rejects_unprotected_main() -> None:
    report = _report(protected=False)
    assert report["passed"] is False
    assert _check(report, "main_protected")["passed"] is False


def test_release_acceptance_requires_ruleset_for_main() -> None:
    report = _report(rulesets=[TAG_RULESET])
    assert report["passed"] is False
    assert _check(report, "main_ruleset")["observed"] == []


def test_release_acceptance_requires_ruleset_for_exact_release_tag() -> None:
    unrelated_tag_ruleset = {
        **TAG_RULESET,
        "conditions": {"ref_name": {"include": ["refs/tags/docs-*"], "exclude": []}},
    }
    report = _report(rulesets=[BRANCH_RULESET, unrelated_tag_ruleset])
    assert report["passed"] is False
    assert _check(report, "release_tag_ruleset")["observed"] == []


def test_release_acceptance_honors_ruleset_exclusions() -> None:
    excluded_tag_ruleset = {
        **TAG_RULESET,
        "conditions": {
            "ref_name": {
                "include": ["refs/tags/v*"],
                "exclude": [f"refs/tags/{TAG}"],
            }
        },
    }
    report = _report(rulesets=[BRANCH_RULESET, excluded_tag_ruleset])
    assert report["passed"] is False
    assert _check(report, "release_tag_ruleset")["passed"] is False


def test_release_acceptance_rejects_existing_tag() -> None:
    report = _report(releases=[{"tag_name": TAG}])
    assert report["passed"] is False
    assert _check(report, "release_tag_unused")["passed"] is False


def test_release_acceptance_requires_immutable_releases() -> None:
    report = _report(immutable=False)
    assert report["passed"] is False
    assert _check(report, "immutable_releases_enabled")["passed"] is False


def test_release_acceptance_requires_exact_production_commit() -> None:
    report = _report(production_commit="b" * 40)
    assert report["passed"] is False
    assert _check(report, "production_commit")["observed"] == "b" * 40


@pytest.mark.parametrize("tag", ["v1.0.0-rc.0", "v1.0.1", "1.0.0", "v1.0.0-beta.1"])
def test_release_acceptance_rejects_out_of_scope_tags(tag: str) -> None:
    with pytest.raises(ReleaseAcceptanceError, match="tag must be"):
        evaluate_acceptance(
            expected_commit=COMMIT,
            release_tag=tag,
            branch={"commit": {"sha": COMMIT}, "protected": True},
            rulesets=[BRANCH_RULESET, TAG_RULESET],
            releases=[],
            immutable_releases={"enabled": True},
            production_headers={"x-compatforge-commit": COMMIT},
        )
