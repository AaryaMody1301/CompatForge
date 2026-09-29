"""Evaluate the external gates required before a CompatForge release is cut."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_RELEASE_TAG = re.compile(
    r"^(?:v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)(?:-rc\.[1-9][0-9]*)?"
    r"|hw-cli-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)(?:rc[1-9][0-9]*)?)$"
)
_API_VERSION = "2026-03-10"
_DEFAULT_REPOSITORY = "AaryaMody1301/CompatForge"
_DEFAULT_BRANCH = "main"
_DEFAULT_PRODUCTION_URL = "https://compat-forge.vercel.app"
_ACTIVE_ENFORCEMENT = frozenset({"active", "enabled", "always"})
_REQUIRED_CHECKS = frozenset({
    "Python contracts", "Next.js web", "Supabase migrations and RLS",
    "Workflow security policy",
})
_RELEASE_CREATION_ACTOR_TYPES = frozenset({"Integration", "Team", "User"})


class ReleaseAcceptanceError(ValueError):
    """Raised when release acceptance cannot be evaluated safely."""


def _validate_commit(commit: str) -> None:
    if not _FULL_SHA.fullmatch(commit):
        raise ReleaseAcceptanceError("commit must be a lowercase 40-character hexadecimal SHA")


def _validate_tag(tag: str) -> None:
    if not _RELEASE_TAG.fullmatch(tag):
        raise ReleaseAcceptanceError(
            "tag must be vMAJOR.MINOR.PATCH[-rc.N] or hw-cli-vMAJOR.MINOR.PATCH[rcN]"
        )


def _request(
    url: str,
    *,
    token: str | None = None,
    method: str = "GET",
) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CompatForge-release-acceptance/1",
        "X-GitHub-Api-Version": _API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers, method=method)


def _fetch_json(url: str, *, token: str | None = None) -> Any:
    try:
        with urllib.request.urlopen(_request(url, token=token), timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ReleaseAcceptanceError(f"could not read required API state from {url}") from exc


def _fetch_immutable_state(url: str, *, token: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(_request(url, token=token), timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"enabled": False, "enforced_by_owner": False}
        raise ReleaseAcceptanceError("could not read immutable release state") from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ReleaseAcceptanceError("could not read immutable release state") from exc
    if not isinstance(payload, dict):
        raise ReleaseAcceptanceError("immutable release state was not a JSON object")
    return payload


def _fetch_headers(url: str) -> dict[str, str]:
    try:
        with urllib.request.urlopen(_request(url, method="HEAD"), timeout=15) as response:
            return {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.URLError as exc:
        message = f"could not read production deployment headers from {url}"
        raise ReleaseAcceptanceError(message) from exc


def _active_rulesets(rulesets: Any) -> list[dict[str, Any]]:
    if not isinstance(rulesets, list):
        return []
    return [
        item
        for item in rulesets
        if isinstance(item, dict) and item.get("enforcement") in _ACTIVE_ENFORCEMENT
    ]


def _ref_matches(pattern: str, ref: str, *, default_branch: bool) -> bool:
    if pattern == "~ALL":
        return True
    if pattern == "~DEFAULT_BRANCH":
        return default_branch
    return fnmatchcase(ref, pattern)


def _ruleset_applies(
    ruleset: dict[str, Any],
    *,
    target: str,
    ref: str,
    default_branch: bool = False,
) -> bool:
    if ruleset.get("enforcement") not in _ACTIVE_ENFORCEMENT:
        return False
    if ruleset.get("target") != target:
        return False
    conditions = ruleset.get("conditions")
    if not isinstance(conditions, dict):
        return False
    ref_name = conditions.get("ref_name")
    if not isinstance(ref_name, dict):
        return False
    includes = ref_name.get("include")
    excludes = ref_name.get("exclude", [])
    if not isinstance(includes, list) or not includes:
        return False
    if not isinstance(excludes, list):
        return False
    included = any(
        isinstance(pattern, str)
        and _ref_matches(pattern, ref, default_branch=default_branch)
        for pattern in includes
    )
    excluded = any(
        isinstance(pattern, str)
        and _ref_matches(pattern, ref, default_branch=default_branch)
        for pattern in excludes
    )
    return included and not excluded


def _ruleset_names(rulesets: list[dict[str, Any]]) -> list[str]:
    return sorted(str(item.get("name", "")) for item in rulesets)


def _rule_types(rulesets: list[dict[str, Any]]) -> set[str]:
    return {
        rule["type"]
        for ruleset in rulesets
        for rule in ruleset.get("rules", [])
        if isinstance(rule, dict) and isinstance(rule.get("type"), str)
    }


def _required_contexts(rulesets: list[dict[str, Any]]) -> set[str]:
    return {
        check["context"]
        for ruleset in rulesets
        for rule in ruleset.get("rules", [])
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks"
        and isinstance(rule.get("parameters"), dict)
        for check in rule["parameters"].get("required_status_checks", [])
        if isinstance(check, dict) and isinstance(check.get("context"), str)
    }


def _bypass_actors(ruleset: dict[str, Any]) -> list[Any]:
    actors = ruleset.get("bypass_actors", [])
    if not isinstance(actors, list):
        return [{"invalid": True}]
    return actors


def _release_tag_policy(
    rulesets: list[dict[str, Any]], expected_actor: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    creation_rulesets = [item for item in rulesets if "creation" in _rule_types([item])]
    protected_rulesets = [
        item for item in rulesets
        if _rule_types([item]) & {"update", "deletion"}
    ]
    actor_id = expected_actor.get("actor_id") if expected_actor is not None else None
    actor_type = expected_actor.get("actor_type") if expected_actor is not None else None
    expected_actor_is_valid = (
        type(actor_id) is int
        and actor_id > 0
        and isinstance(actor_type, str)
        and actor_type in _RELEASE_CREATION_ACTOR_TYPES
    )
    creation_actor = (
        {
            "actor_id": actor_id,
            "actor_type": actor_type,
            "bypass_mode": "always",
        }
        if expected_actor_is_valid
        else None
    )
    creation_is_restricted = (
        bool(creation_rulesets)
        and creation_actor is not None
        and all(
            _rule_types([ruleset]) == {"creation"}
            and _bypass_actors(ruleset) == [creation_actor]
            for ruleset in creation_rulesets
        )
    )
    protected_types = _rule_types(
        [ruleset for ruleset in protected_rulesets if not _bypass_actors(ruleset)]
    )
    update_delete_are_protected = (
        {"update", "deletion"}.issubset(protected_types)
        and all(not _bypass_actors(ruleset) for ruleset in protected_rulesets)
    )
    passed = creation_is_restricted and update_delete_are_protected
    observed = {
        "creation_rulesets": [
            {"name": item.get("name", ""), "bypass_actors": _bypass_actors(item)}
            for item in creation_rulesets
        ],
        "protected_rulesets": [
            {"name": item.get("name", ""), "rules": sorted(_rule_types([item])),
             "bypass_actors": _bypass_actors(item)}
            for item in protected_rulesets
        ],
        "expected_creation_actor": creation_actor,
        "creation_restricted_to_expected_actor": creation_is_restricted,
        "updates_and_deletion_have_no_bypass": update_delete_are_protected,
    }
    return passed, observed


def evaluate_acceptance(
    *,
    expected_commit: str,
    release_tag: str,
    branch: dict[str, Any],
    rulesets: Any,
    releases: Any,
    immutable_releases: dict[str, Any],
    production_headers: dict[str, str],
    release_creation_actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a bounded report over repository, release, and production state."""

    _validate_commit(expected_commit)
    _validate_tag(release_tag)
    checks: list[dict[str, Any]] = []

    branch_commit = ((branch.get("commit") or {}).get("sha")) if isinstance(branch, dict) else None
    checks.append(
        {
            "name": "main_commit",
            "passed": branch_commit == expected_commit,
            "observed": branch_commit,
        }
    )
    checks.append(
        {
            "name": "main_protected",
            "passed": bool(branch.get("protected")) if isinstance(branch, dict) else False,
            "observed": bool(branch.get("protected")) if isinstance(branch, dict) else False,
        }
    )

    active_rulesets = _active_rulesets(rulesets)
    main_ref = f"refs/heads/{_DEFAULT_BRANCH}"
    main_rulesets = [
        item
        for item in active_rulesets
        if _ruleset_applies(item, target="branch", ref=main_ref, default_branch=True)
    ]
    checks.append(
        {
            "name": "main_ruleset",
            "passed": bool(main_rulesets) and {
                "pull_request", "non_fast_forward", "deletion", "required_status_checks"
            }.issubset(_rule_types(main_rulesets))
            and _REQUIRED_CHECKS.issubset(_required_contexts(main_rulesets))
            and all(not _bypass_actors(item) for item in main_rulesets),
            "observed": {"names": _ruleset_names(main_rulesets),
                         "rules": sorted(_rule_types(main_rulesets)),
                         "checks": sorted(_required_contexts(main_rulesets)),
                         "bypass_actors": {
                             str(item.get("name", "")): _bypass_actors(item)
                             for item in main_rulesets
                         }},
        }
    )

    tag_ref = f"refs/tags/{release_tag}"
    tag_rulesets = [
        item
        for item in active_rulesets
        if _ruleset_applies(item, target="tag", ref=tag_ref)
    ]
    tag_policy_passed, tag_policy_observed = _release_tag_policy(
        tag_rulesets, release_creation_actor
    )
    checks.append(
        {
            "name": "release_tag_ruleset",
            "passed": bool(tag_rulesets) and tag_policy_passed,
            "observed": {"names": _ruleset_names(tag_rulesets),
                         "rules": sorted(_rule_types(tag_rulesets)), **tag_policy_observed},
        }
    )

    release_items = releases if isinstance(releases, list) else []
    existing_tags = sorted(
        str(item.get("tag_name"))
        for item in release_items
        if isinstance(item, dict) and item.get("tag_name")
    )
    checks.append(
        {
            "name": "release_tag_unused",
            "passed": release_tag not in existing_tags,
            "observed": release_tag in existing_tags,
        }
    )

    immutable_enabled = immutable_releases.get("enabled") is True
    checks.append(
        {
            "name": "immutable_releases_enabled",
            "passed": immutable_enabled,
            "observed": immutable_enabled,
        }
    )

    production_commit = production_headers.get("x-compatforge-commit")
    checks.append(
        {
            "name": "production_commit",
            "passed": production_commit == expected_commit,
            "observed": production_commit,
        }
    )

    return {
        "schema_version": "1.0.0",
        "source_commit": expected_commit,
        "release_tag": release_tag,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def _fetch_ruleset_details(
    *,
    base_url: str,
    summaries: Any,
    token: str,
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for summary in _active_rulesets(summaries):
        ruleset_id = summary.get("id")
        if not isinstance(ruleset_id, int):
            continue
        payload = _fetch_json(
            f"{base_url}/rulesets/{ruleset_id}?includes_parents=true",
            token=token,
        )
        if isinstance(payload, dict):
            details.append(payload)
    return details


def inspect_live_state(
    *,
    repository: str,
    branch_name: str,
    production_url: str,
    expected_commit: str,
    release_tag: str,
    github_token: str,
    release_creation_actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch live GitHub/Vercel state and evaluate release readiness."""

    _validate_commit(expected_commit)
    _validate_tag(release_tag)
    base = f"https://api.github.com/repos/{repository}"
    branch = _fetch_json(f"{base}/branches/{branch_name}", token=github_token)
    summaries = _fetch_json(f"{base}/rulesets?includes_parents=true", token=github_token)
    rulesets = _fetch_ruleset_details(base_url=base, summaries=summaries, token=github_token)
    releases = _fetch_json(f"{base}/releases?per_page=100", token=github_token)
    immutable_releases = _fetch_immutable_state(
        f"{base}/immutable-releases",
        token=github_token,
    )
    production_headers = _fetch_headers(production_url.rstrip("/") + "/")
    return evaluate_acceptance(
        expected_commit=expected_commit,
        release_tag=release_tag,
        branch=branch,
        rulesets=rulesets,
        releases=releases,
        immutable_releases=immutable_releases,
        production_headers=production_headers,
        release_creation_actor=release_creation_actor,
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CompatForge release acceptance",
        "",
        f"- Commit: `{report['source_commit']}`",
        f"- Tag: `{report['release_tag']}`",
        f"- Result: **{'PASS' if report['passed'] else 'FAIL'}**",
        "",
        "| Gate | Result | Observed |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        observed = json.dumps(check["observed"], sort_keys=True)
        lines.append(
            f"| `{check['name']}` | {'PASS' if check['passed'] else 'FAIL'} | `{observed}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=_DEFAULT_REPOSITORY)
    parser.add_argument("--branch", default=_DEFAULT_BRANCH)
    parser.add_argument("--production-url", default=_DEFAULT_PRODUCTION_URL)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--github-token-env",
        default="COMPATFORGE_RELEASE_ADMIN_TOKEN",
        help="environment variable holding a fine-grained GitHub token with Administration: read",
    )
    parser.add_argument("--output", type=Path, default=Path("build/release-acceptance/report.json"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    token = os.environ.get(args.github_token_env, "").strip()
    if not token:
        message = (
            f"release acceptance failed: {args.github_token_env} is required "
            "to verify immutable releases"
        )
        print(message, file=sys.stderr)
        return 1
    actor_type = os.environ.get("COMPATFORGE_RELEASE_CREATION_ACTOR_TYPE", "").strip()
    actor_id_value = os.environ.get("COMPATFORGE_RELEASE_CREATION_ACTOR_ID", "").strip()
    release_creation_actor: dict[str, Any] | None = None
    if actor_type and actor_id_value:
        try:
            actor_id = int(actor_id_value)
        except ValueError:
            actor_id = 0
        if actor_id > 0:
            release_creation_actor = {"actor_type": actor_type, "actor_id": actor_id}
    try:
        report = inspect_live_state(
            repository=args.repository,
            branch_name=args.branch,
            production_url=args.production_url,
            expected_commit=args.commit,
            release_tag=args.tag,
            github_token=token,
            release_creation_actor=release_creation_actor,
        )
        _write_report(report, args.output)
        print(render_markdown(report))
        return 0 if report["passed"] else 1
    except (ReleaseAcceptanceError, OSError, TypeError, KeyError) as exc:
        print(f"release acceptance failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
