"""Build and verify immutable CompatForge release provenance manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
DEFAULT_REPOSITORY = "AaryaMody1301/CompatForge"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

SOURCE_GROUPS: dict[str, tuple[str, ...]] = {
    "identity": (
        "data/catalog",
        "data/sources/usb_ids.json",
        "apps/web/src/lib/catalog.ts",
        "pipeline/compatforge_pipeline/usb_ids.py",
    ),
    "evidence": (
        "data/evidence/observations",
        "data/evidence/vendor",
        "data/sources/vendor-adapters",
        "pipeline/compatforge_pipeline/resources/local_snapshot.json",
    ),
    "web": (
        "apps/web/package.json",
        "apps/web/package-lock.json",
        "apps/web/next.config.ts",
        "apps/web/src",
    ),
    "transformations": (
        "dbt/compatforge",
        "pipeline/compatforge_pipeline/identity_pipeline.py",
        "pipeline/compatforge_pipeline/evidence_pipeline.py",
    ),
}


class ReleaseManifestError(ValueError):
    """Raised when release provenance cannot be built or verified safely."""


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_commit(commit: str) -> None:
    if not _COMMIT_RE.fullmatch(commit):
        raise ReleaseManifestError("commit must be a lowercase 40-character hexadecimal SHA")


def _resolve_within(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ReleaseManifestError(f"path escapes its declared root: {relative}") from exc
    if not candidate.exists():
        raise ReleaseManifestError(f"required path does not exist: {relative}")
    return candidate


def _file_entry(root: Path, path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ReleaseManifestError(f"release provenance refuses symlink: {path}")
    if not path.is_file():
        raise ReleaseManifestError(f"release provenance expected a file: {path}")
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return {
        "path": relative,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _collect_path(root: Path, relative: str) -> list[dict[str, Any]]:
    root = root.resolve()
    target = _resolve_within(root, relative)
    if target.is_symlink():
        raise ReleaseManifestError(f"release provenance refuses symlink: {relative}")
    if target.is_file():
        return [_file_entry(root, target)]
    if not target.is_dir():
        raise ReleaseManifestError(f"unsupported release provenance path: {relative}")

    files = sorted(
        (item for item in target.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    )
    if not files:
        raise ReleaseManifestError(f"release provenance directory is empty: {relative}")
    return [_file_entry(root, item) for item in files]


def collect_source_groups(repository_root: Path) -> dict[str, dict[str, Any]]:
    """Hash the reviewed repository inputs that define released behavior and data."""

    groups: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for group_name, paths in SOURCE_GROUPS.items():
        entries: list[dict[str, Any]] = []
        for relative in paths:
            for entry in _collect_path(repository_root, relative):
                if entry["path"] in seen:
                    continue
                seen.add(entry["path"])
                entries.append(entry)
        entries.sort(key=lambda item: item["path"])
        groups[group_name] = {
            "file_count": len(entries),
            "files": entries,
            "group_sha256": _canonical_sha256(entries),
        }
    return dict(sorted(groups.items()))


def _artifact_entry(release_root: Path, relative: str) -> dict[str, Any]:
    target = _resolve_within(release_root, relative)
    if target.is_symlink() or not target.is_file():
        raise ReleaseManifestError(f"release artifact must be a regular file: {relative}")
    return _file_entry(release_root, target)


def build_manifest(
    *,
    repository_root: Path,
    release_root: Path,
    commit: str,
    release_name: str,
    artifact_paths: list[str],
    repository: str = DEFAULT_REPOSITORY,
) -> dict[str, Any]:
    """Build a deterministic manifest over reviewed source inputs and release artifacts."""

    _validate_commit(commit)
    if not release_name.strip():
        raise ReleaseManifestError("release_name must not be empty")
    if not artifact_paths:
        raise ReleaseManifestError("at least one release artifact is required")

    artifacts = [_artifact_entry(release_root, path) for path in artifact_paths]
    artifacts.sort(key=lambda item: item["path"])
    if len({item["path"] for item in artifacts}) != len(artifacts):
        raise ReleaseManifestError("release artifact paths must be unique")

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "release_name": release_name,
        "repository": repository,
        "source_commit": commit,
        "source_groups": collect_source_groups(repository_root),
        "release_artifacts": artifacts,
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
    return manifest


def _render_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def write_release_files(
    *,
    manifest: dict[str, Any],
    release_root: Path,
    manifest_name: str = "COMPATFORGE_RELEASE_MANIFEST.json",
    checksums_name: str = "SHA256SUMS.txt",
) -> tuple[Path, Path]:
    """Write the immutable manifest and a conventional checksum index."""

    release_root.mkdir(parents=True, exist_ok=True)
    manifest_path = release_root / manifest_name
    checksums_path = release_root / checksums_name
    manifest_path.write_text(_render_manifest(manifest), encoding="utf-8")

    checksum_entries = [
        *manifest["release_artifacts"],
        _file_entry(release_root, manifest_path),
    ]
    checksum_entries.sort(key=lambda item: item["path"])
    checksums = "".join(f"{item['sha256']}  {item['path']}\n" for item in checksum_entries)
    checksums_path.write_text(checksums, encoding="utf-8", newline="\n")
    return manifest_path, checksums_path


def _verify_manifest_hash(manifest: dict[str, Any]) -> None:
    expected = manifest.get("manifest_sha256")
    if not isinstance(expected, str):
        raise ReleaseManifestError("manifest_sha256 is missing")
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    actual = _canonical_sha256(unsigned)
    if actual != expected:
        raise ReleaseManifestError("release manifest self-hash does not match")


def verify_manifest(
    *,
    manifest_path: Path,
    repository_root: Path,
    release_root: Path,
    expected_commit: str | None = None,
) -> dict[str, Any]:
    """Recompute every source and artifact digest recorded by a release manifest."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError("release manifest could not be loaded") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseManifestError("unsupported release manifest schema_version")

    commit = manifest.get("source_commit")
    if not isinstance(commit, str):
        raise ReleaseManifestError("release manifest source_commit is missing")
    _validate_commit(commit)
    if expected_commit is not None and commit != expected_commit:
        raise ReleaseManifestError("release manifest source_commit does not match expected commit")

    _verify_manifest_hash(manifest)

    actual_groups = collect_source_groups(repository_root)
    if actual_groups != manifest.get("source_groups"):
        raise ReleaseManifestError("reviewed repository source hashes do not match release manifest")

    recorded_artifacts = manifest.get("release_artifacts")
    if not isinstance(recorded_artifacts, list) or not recorded_artifacts:
        raise ReleaseManifestError("release manifest has no release_artifacts")
    actual_artifacts = [
        _artifact_entry(release_root, str(item["path"])) for item in recorded_artifacts
    ]
    actual_artifacts.sort(key=lambda item: item["path"])
    if actual_artifacts != recorded_artifacts:
        raise ReleaseManifestError("release artifact hashes do not match release manifest")
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build immutable release provenance files")
    build.add_argument("--repository-root", type=Path, default=Path("."))
    build.add_argument("--release-root", type=Path, required=True)
    build.add_argument("--commit", required=True)
    build.add_argument("--release-name", required=True)
    build.add_argument("--artifact", action="append", dest="artifacts", required=True)
    build.add_argument("--repository", default=DEFAULT_REPOSITORY)

    verify = commands.add_parser("verify", help="verify release provenance and artifact hashes")
    verify.add_argument("--repository-root", type=Path, default=Path("."))
    verify.add_argument("--release-root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--expected-commit")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "build":
            manifest = build_manifest(
                repository_root=args.repository_root,
                release_root=args.release_root,
                commit=args.commit,
                release_name=args.release_name,
                artifact_paths=args.artifacts,
                repository=args.repository,
            )
            manifest_path, checksums_path = write_release_files(
                manifest=manifest,
                release_root=args.release_root,
            )
            print(
                f"wrote release manifest {manifest_path} and checksums {checksums_path} "
                f"sha256={manifest['manifest_sha256']}"
            )
            return 0

        manifest = verify_manifest(
            manifest_path=args.manifest,
            repository_root=args.repository_root,
            release_root=args.release_root,
            expected_commit=args.expected_commit,
        )
        print(f"verified release manifest sha256={manifest['manifest_sha256']}")
        return 0
    except (ReleaseManifestError, OSError, KeyError, TypeError) as exc:
        print(f"release manifest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
