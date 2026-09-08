from pathlib import Path

from compatforge_pipeline.workflow_security import validate_workflow, validate_workflow_directory


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "workflow.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_repository_workflows_satisfy_security_policy() -> None:
    assert validate_workflow_directory(Path(".github/workflows")) == {}


def test_policy_allows_github_major_tags_and_pinned_third_party(tmp_path: Path) -> None:
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
      - uses: actions/checkout@v6
      - uses: github/codeql-action/analyze@v4
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


def test_policy_rejects_mutable_third_party_action(tmp_path: Path) -> None:
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
      - uses: vendor/tool@v2
""",
    )
    assert validate_workflow(path) == [
        "external action must use a full commit SHA, or a major tag for GitHub-maintained actions: vendor/tool@v2"
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
