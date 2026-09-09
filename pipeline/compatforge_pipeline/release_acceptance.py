"""Evaluate the external gates required before a CompatForge release is cut."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_RELEASE_TAG = re.compile(r"^v1\.0\.0(?:-rc\.[1-9][0-9]*)?$")
_API_VERSION = "2026-03-10"
_DEFAULT_REPOSITORY = "AaryaMody1301/CompatForge"
_DEFAULT_BRANCH = "main"
_DEFAULT_PRODUCTION_URL = "https://compat-forge.vercel.app"


class ReleaseAcceptanceError(ValueError):
    """Raised when release acceptance cannot be evaluated safely."""


def _validate_commit(commit: str) -> None:
    if not _FULL_SHA.fullmatch(commit):
        raise ReleaseAcceptanceError("commit must be a lowercase 40-character hexadecimal SHA")


def _validate_tag(tag: str) -> None:
    if not _RELEASE_TAG.fullmatch(tag):
        raise ReleaseAcceptanceError("tag must be v1.0.0 or v1.0.0-rc.N")


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


def _fetch_headers(url: str) -> dict[str, str]:
    try:
        with urllib.request.urlopen(_request(url, method="HEAD"), timeout=15) as response:
            return {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.URLError as exc:
        raise ReleaseAcceptanceError(f"could not read production deployment headers from {url}") from exc


def _active_rulesets(rulesets: Any) -> list[dict[str, Any]]:
    if not isinstance(rulesets, list):
        return []
    return [
        item
        for item in rulesets
        if isinstance(item, dict) and item.get("enforcement") in {"active", "always"}
    ]


def evaluate_acceptance(
    *,
    expected_commit: str,
    release_tag: str,
    branch: dict[str, Any],
    rulesets: Any,
    releases: Any,
    immutable_releases: dict[str, Any],
    production_headers: dict[str, str],
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
    checks.append(
        {
            "name": "active_repository_ruleset",
            "passed": bool(active_rulesets),
            "observed": sorted(str(item.get("name", "")) for item in active_rulesets),
        }
    )

    existing_tags = sorted(
        str(item.get("tag_name"))
        for item in releases
        if isinstance(releases, list) and isinstance(item, dict) and item.get("tag_name")
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


def inspect_live_state(
    *,
    repository: str,
    branch_name: str,
    production_url: str,
    expected_commit: str,
    release_tag: str,
    github_token: str,
) -> dict[str, Any]:
    """Fetch live GitHub/Vercel state and evaluate release readiness."""

    _validate_commit(expected_commit)
    _validate_tag(release_tag)
    base = f"https://api.github.com/repos/{repository}"
    branch = _fetch_json(f"{base}/branches/{branch_name}", token=github_token)
    rulesets = _fetch_json(f"{base}/rulesets?includes_parents=true", token=github_token)
    releases = _fetch_json(f"{base}/releases?per_page=100", token=github_token)
    immutable_releases = _fetch_json(f"{base}/immutable-releases", token=github_token)
    production_headers = _fetch_headers(production_url.rstrip("/") + "/")
    return evaluate_acceptance(
        expected_commit=expected_commit,
        release_tag=release_tag,
        branch=branch,
        rulesets=rulesets,
        releases=releases,
        immutable_releases=immutable_releases,
        production_headers=production_headers,
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
        print(
            f"release acceptance failed: {args.github_token_env} is required to verify immutable releases",
            file=sys.stderr,
        )
        return 1
    try:
        report = inspect_live_state(
            repository=args.repository,
            branch_name=args.branch,
            production_url=args.production_url,
            expected_commit=args.commit,
            release_tag=args.tag,
            github_token=token,
        )
        _write_report(report, args.output)
        print(render_markdown(report))
        return 0 if report["passed"] else 1
    except (ReleaseAcceptanceError, OSError, TypeError, KeyError) as exc:
        print(f"release acceptance failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
