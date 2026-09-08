"""Static security policy checks for CompatForge GitHub Actions workflows."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
MAJOR_TAG = re.compile(r"^v[1-9][0-9]*$")
USES_LINE = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
TOP_LEVEL_PERMISSIONS = re.compile(r"^permissions:\s*$", re.MULTILINE)
PULL_REQUEST_TARGET = re.compile(r"^\s*pull_request_target\s*:", re.MULTILINE)
DANGEROUS_PIPE = re.compile(
    r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|fi)?sh\b",
    re.IGNORECASE,
)
OFFICIAL_MUTABLE_ACTION_OWNERS = frozenset({"actions", "github"})


def _action_error(reference: str) -> str | None:
    if reference.startswith("./") or reference.startswith("docker://"):
        return None
    if "@" not in reference:
        return f"external action reference has no version: {reference}"

    action, version = reference.rsplit("@", 1)
    owner = action.split("/", 1)[0]
    if FULL_SHA.fullmatch(version):
        return None
    if owner in OFFICIAL_MUTABLE_ACTION_OWNERS and MAJOR_TAG.fullmatch(version):
        return None
    return (
        f"external action must use a full commit SHA, or a major tag for GitHub-maintained "
        f"actions: {reference}"
    )


def validate_workflow(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    if not TOP_LEVEL_PERMISSIONS.search(text):
        errors.append("workflow must declare explicit top-level permissions")
    if PULL_REQUEST_TARGET.search(text):
        errors.append("pull_request_target is prohibited")
    if DANGEROUS_PIPE.search(text):
        errors.append("network-fetched content must not be piped directly into a shell")

    for reference in USES_LINE.findall(text):
        action_error = _action_error(reference)
        if action_error:
            errors.append(action_error)

    return errors


def validate_workflow_directory(directory: Path) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {}
    for path in sorted((*directory.glob("*.yml"), *directory.glob("*.yaml"))):
        errors = validate_workflow(path)
        if errors:
            findings[path.as_posix()] = errors
    return findings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path(".github/workflows"),
        help="workflow directory to validate",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    findings = validate_workflow_directory(args.directory)
    if not findings:
        print(f"workflow security policy passed for {args.directory}")
        return 0

    for path, errors in findings.items():
        for error in errors:
            print(f"{path}: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
