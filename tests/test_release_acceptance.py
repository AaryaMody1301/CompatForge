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
    "rules": [
        {"type": "pull_request"}, {"type": "non_fast_forward"}, {"type": "deletion"},
        {"type": "required_status_checks", "parameters": {"required_status_checks": [
            {"context": name} for name in (
                "Python contracts", "Next.js web", "Supabase migrations and RLS",
                "Workflow security policy",
            )
        ]}},
    ],
}
RELEASE_CREATION_ACTOR = {"actor_type": "User", "actor_id": 42}
TAG_CREATION_RULESET = {
    "name": "release tag creation",
    "target": "tag",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
    "bypass_actors": [{**RELEASE_CREATION_ACTOR, "bypass_mode": "always"}],
    "rules": [{"type": "creation"}],
}
TAG_PROTECTION_RULESET = {
    "name": "release tag immutability",
    "target": "tag",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
    "bypass_actors": [],
    "rules": [{"type": "update"}, {"type": "deletion"}],
}


def _report(
    *,
    protected: bool = True,
    rulesets: list[dict] | None = None,
    releases: list[dict] | None = None,
    immutable: bool = True,
    production_commit: str = COMMIT,
    release_creation_actor: dict | None = RELEASE_CREATION_ACTOR,
) -> dict:
    return evaluate_acceptance(
        expected_commit=COMMIT,
        release_tag=TAG,
        branch={"commit": {"sha": COMMIT}, "protected": protected},
        rulesets=[BRANCH_RULESET, TAG_CREATION_RULESET, TAG_PROTECTION_RULESET]
        if rulesets is None else rulesets,
        releases=[] if releases is None else releases,
        immutable_releases={"enabled": immutable, "enforced_by_owner": False},
        production_headers={"x-compatforge-commit": production_commit},
        release_creation_actor=release_creation_actor,
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
    report = _report(rulesets=[TAG_CREATION_RULESET, TAG_PROTECTION_RULESET])
    assert report["passed"] is False
    assert _check(report, "main_ruleset")["observed"]["names"] == []


def test_release_acceptance_requires_ruleset_for_exact_release_tag() -> None:
    unrelated_tag_ruleset = {
        **TAG_CREATION_RULESET,
        "conditions": {"ref_name": {"include": ["refs/tags/docs-*"], "exclude": []}},
    }
    report = _report(rulesets=[BRANCH_RULESET, unrelated_tag_ruleset])
    assert report["passed"] is False
    assert _check(report, "release_tag_ruleset")["observed"]["names"] == []


def test_empty_rulesets_do_not_pass_protection_gate() -> None:
    report = _report(rulesets=[
        {**BRANCH_RULESET, "rules": []},
        {**TAG_CREATION_RULESET, "rules": []},
        {**TAG_PROTECTION_RULESET, "rules": []},
    ])
    assert report["passed"] is False
    assert not _check(report, "main_ruleset")["passed"]
    assert not _check(report, "release_tag_ruleset")["passed"]


def test_partial_checks_do_not_satisfy_main_protection() -> None:
    incomplete = {**BRANCH_RULESET, "rules": BRANCH_RULESET["rules"][:-1]}
    assert not _check(
        _report(rulesets=[incomplete, TAG_CREATION_RULESET, TAG_PROTECTION_RULESET]),
        "main_ruleset",
    )["passed"]


def test_patch_release_is_valid() -> None:
    report = evaluate_acceptance(
        expected_commit=COMMIT, release_tag="v1.0.1",
        branch={"commit": {"sha": COMMIT}, "protected": True},
        rulesets=[BRANCH_RULESET, TAG_CREATION_RULESET, TAG_PROTECTION_RULESET], releases=[],
        immutable_releases={"enabled": True},
        production_headers={"x-compatforge-commit": COMMIT},
        release_creation_actor=RELEASE_CREATION_ACTOR,
    )
    assert report["passed"] is True


def test_hardware_cli_tag_requires_its_own_protected_ruleset() -> None:
    hardware_creation = {**TAG_CREATION_RULESET, "conditions": {
        "ref_name": {"include": ["refs/tags/hw-cli-v*"], "exclude": []}
    }}
    hardware_protection = {**TAG_PROTECTION_RULESET, "conditions": {
        "ref_name": {"include": ["refs/tags/hw-cli-v*"], "exclude": []}
    }}
    kwargs = dict(
        expected_commit=COMMIT, release_tag="hw-cli-v0.3.0rc1",
        branch={"commit": {"sha": COMMIT}, "protected": True}, releases=[],
        immutable_releases={"enabled": True},
        production_headers={"x-compatforge-commit": COMMIT},
        release_creation_actor=RELEASE_CREATION_ACTOR,
    )
    assert not _check(evaluate_acceptance(rulesets=[
        BRANCH_RULESET, TAG_CREATION_RULESET, TAG_PROTECTION_RULESET,
    ], **kwargs),
                      "release_tag_ruleset")["passed"]
    assert evaluate_acceptance(rulesets=[
        BRANCH_RULESET, hardware_creation, hardware_protection,
    ], **kwargs)["passed"]


def test_release_acceptance_honors_ruleset_exclusions() -> None:
    excluded_tag_ruleset = {
        **TAG_CREATION_RULESET,
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


def test_release_creation_is_limited_to_the_configured_actor() -> None:
    report = _report(rulesets=[
        BRANCH_RULESET,
        {**TAG_CREATION_RULESET, "bypass_actors": [
            {**RELEASE_CREATION_ACTOR, "bypass_mode": "always"},
            {"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"},
        ]},
        TAG_PROTECTION_RULESET,
    ])
    assert not _check(report, "release_tag_ruleset")["passed"]


def test_release_creation_actor_must_be_explicitly_configured() -> None:
    report = _report(release_creation_actor=None)
    assert not _check(report, "release_tag_ruleset")["passed"]


def test_release_tag_updates_and_deletion_have_no_bypass() -> None:
    report = _report(rulesets=[
        BRANCH_RULESET,
        TAG_CREATION_RULESET,
        {**TAG_PROTECTION_RULESET, "bypass_actors": [
            {"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"},
        ]},
    ])
    assert not _check(report, "release_tag_ruleset")["passed"]


def test_main_rulesets_reject_unrestricted_bypass_actors() -> None:
    bypassable_main = {
        **BRANCH_RULESET,
        "bypass_actors": [
            {"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"}
        ],
    }
    report = _report(rulesets=[
        bypassable_main, TAG_CREATION_RULESET, TAG_PROTECTION_RULESET,
    ])
    assert not _check(report, "main_ruleset")["passed"]


@pytest.mark.parametrize("tag", ["v1.0.0-rc.0", "v01.0.1", "1.0.0", "v1.0.0-beta.1"])
def test_release_acceptance_rejects_out_of_scope_tags(tag: str) -> None:
    with pytest.raises(ReleaseAcceptanceError, match="tag must be"):
        evaluate_acceptance(
            expected_commit=COMMIT,
            release_tag=tag,
            branch={"commit": {"sha": COMMIT}, "protected": True},
            rulesets=[BRANCH_RULESET, TAG_CREATION_RULESET, TAG_PROTECTION_RULESET],
            releases=[],
            immutable_releases={"enabled": True},
            production_headers={"x-compatforge-commit": COMMIT},
            release_creation_actor=RELEASE_CREATION_ACTOR,
        )
