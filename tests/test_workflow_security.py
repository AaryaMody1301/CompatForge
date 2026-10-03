import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from compatforge_pipeline.workflow_security import validate_workflow, validate_workflow_directory


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "workflow.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_repository_workflows_satisfy_security_policy() -> None:
    assert validate_workflow_directory(Path(".github/workflows")) == {}


@pytest.mark.skipif(shutil.which("bash") is None, reason="workflow runs on Ubuntu with Bash")
@pytest.mark.parametrize(
    ("mode", "token", "status", "output"),
    [
        ("candidate", "", 0, "ready=false"),
        ("candidate", "test-token", 0, "ready=false"),
        ("review-pr", "", 1, ""),
        ("review-pr", "test-token", 0, "ready=true"),
        ("invalid", "test-token", 1, ""),
    ],
)
def test_identity_refresh_mode_enforces_write_credentials(
    tmp_path: Path, mode: str, token: str, status: int, output: str
) -> None:
    # Execute the actual workflow guard so candidate mode cannot silently enable writes.
    workflow = Path(".github/workflows/refresh-identities.yml").read_text()
    guard = workflow.split("- name: Check refresh mode and write configuration", 1)[1]
    script = re.search(r"        run: \|\n((?:          .*\n)+)", guard)
    assert script is not None
    output_path = tmp_path / "output"
    output_path.touch()
    result = subprocess.run(
        ["bash", "-e", "-c", "\n".join(line[10:] for line in script[1].splitlines())],
        env={
            **os.environ,
            "REFRESH_MODE": mode,
            "REFRESH_GITHUB_TOKEN": token,
            "GITHUB_OUTPUT": str(output_path),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == status
    assert output_path.read_text().strip() == output
    assert "test-token" not in result.stdout + result.stderr


def test_policy_allows_only_pinned_external_actions(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """name: ok
on: pull_request
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      - uses: github/codeql-action/analyze@cdf488f595d80d6e07e03d4674febd5ab45fa938
      - uses: vendor/tool@0123456789abcdef0123456789abcdef01234567
""",
    )
    assert validate_workflow(path) == []


def test_policy_rejects_missing_permissions_and_pull_request_target(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """name: unsafe
on:
  pull_request_target:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo unsafe
""",
    )
    assert validate_workflow(path) == [
        "workflow must declare explicit top-level permissions",
        "pull_request_target is prohibited",
    ]


def test_policy_rejects_mutable_external_actions(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """name: unsafe
on: pull_request
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v7
      - uses: github/codeql-action/analyze@v4
      - uses: vendor/tool@v2
""",
    )
    assert validate_workflow(path) == [
        "external action must use a full 40-character commit SHA: actions/setup-python@v7",
        "external action must use a full 40-character commit SHA: github/codeql-action/analyze@v4",
        "external action must use a full 40-character commit SHA: vendor/tool@v2",
    ]


def test_policy_rejects_network_content_piped_to_shell(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """name: unsafe
on: push
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: curl -fsSL https://example.invalid/install.sh | bash
""",
    )
    assert validate_workflow(path) == [
        "network-fetched content must not be piped directly into a shell"
    ]
