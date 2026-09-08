from __future__ import annotations

import json
from pathlib import Path

import pytest

from compatforge_pipeline import release_manifest
from compatforge_pipeline.release_manifest import (
    ReleaseManifestError,
    build_manifest,
    verify_manifest,
    write_release_files,
)

COMMIT = "a" * 40


def _fixture_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    repository_root = tmp_path / "repository"
    release_root = tmp_path / "release"
    (repository_root / "identity").mkdir(parents=True)
    (repository_root / "evidence").mkdir()
    (repository_root / "web").mkdir()
    (repository_root / "transform").mkdir()
    release_root.mkdir()

    (repository_root / "identity" / "catalog.json").write_text(
        '{"device":"usb:0403:6001"}\n', encoding="utf-8"
    )
    (repository_root / "evidence" / "observation.json").write_text(
        '{"outcome":"works"}\n', encoding="utf-8"
    )
    (repository_root / "web" / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n', encoding="utf-8"
    )
    (repository_root / "transform" / "model.sql").write_text(
        "select 1 as device_count\n", encoding="utf-8"
    )
    (release_root / "compatforge-web-build.tar.gz").write_bytes(b"web-build")
    (release_root / "compatforge-web.spdx.json").write_text(
        '{"spdxVersion":"SPDX-2.3"}\n', encoding="utf-8"
    )

    monkeypatch.setattr(
        release_manifest,
        "SOURCE_GROUPS",
        {
            "identity": ("identity",),
            "evidence": ("evidence",),
            "web": ("web",),
            "transformations": ("transform",),
        },
    )
    return repository_root, release_root


def _build(repository_root: Path, release_root: Path) -> dict:
    return build_manifest(
        repository_root=repository_root,
        release_root=release_root,
        commit=COMMIT,
        release_name="compatforge-test",
        artifact_paths=["compatforge-web-build.tar.gz", "compatforge-web.spdx.json"],
    )


def test_release_manifest_is_deterministic_and_verifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, release_root = _fixture_roots(tmp_path, monkeypatch)

    first = _build(repository_root, release_root)
    second = _build(repository_root, release_root)
    assert first == second
    assert first["source_commit"] == COMMIT
    assert first["source_groups"]["evidence"]["file_count"] == 1

    manifest_path, checksums_path = write_release_files(
        manifest=first,
        release_root=release_root,
    )
    verified = verify_manifest(
        manifest_path=manifest_path,
        repository_root=repository_root,
        release_root=release_root,
        expected_commit=COMMIT,
    )
    assert verified == first

    checksums = checksums_path.read_text(encoding="utf-8")
    assert "compatforge-web-build.tar.gz" in checksums
    assert "compatforge-web.spdx.json" in checksums
    assert "COMPATFORGE_RELEASE_MANIFEST.json" in checksums


def test_release_manifest_detects_artifact_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, release_root = _fixture_roots(tmp_path, monkeypatch)
    manifest = _build(repository_root, release_root)
    manifest_path, _ = write_release_files(manifest=manifest, release_root=release_root)
    (release_root / "compatforge-web-build.tar.gz").write_bytes(b"tampered")

    with pytest.raises(ReleaseManifestError, match="release artifact hashes"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=repository_root,
            release_root=release_root,
        )


def test_release_manifest_detects_reviewed_source_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, release_root = _fixture_roots(tmp_path, monkeypatch)
    manifest = _build(repository_root, release_root)
    manifest_path, _ = write_release_files(manifest=manifest, release_root=release_root)
    (repository_root / "evidence" / "observation.json").write_text(
        '{"outcome":"fails"}\n', encoding="utf-8"
    )

    with pytest.raises(ReleaseManifestError, match="reviewed repository source hashes"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=repository_root,
            release_root=release_root,
        )


def test_release_manifest_rejects_commit_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, release_root = _fixture_roots(tmp_path, monkeypatch)
    manifest = _build(repository_root, release_root)
    manifest_path, _ = write_release_files(manifest=manifest, release_root=release_root)

    with pytest.raises(ReleaseManifestError, match="source_commit does not match"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=repository_root,
            release_root=release_root,
            expected_commit="b" * 40,
        )


def test_release_manifest_self_hash_detects_manifest_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, release_root = _fixture_roots(tmp_path, monkeypatch)
    manifest = _build(repository_root, release_root)
    manifest_path, _ = write_release_files(manifest=manifest, release_root=release_root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["release_name"] = "edited"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReleaseManifestError, match="self-hash"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=repository_root,
            release_root=release_root,
        )


def test_release_manifest_rejects_non_full_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, release_root = _fixture_roots(tmp_path, monkeypatch)
    with pytest.raises(ReleaseManifestError, match="40-character"):
        build_manifest(
            repository_root=repository_root,
            release_root=release_root,
            commit="abc123",
            release_name="compatforge-test",
            artifact_paths=["compatforge-web-build.tar.gz"],
        )
