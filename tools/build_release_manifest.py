"""Generate checksums and a machine-readable CLI release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(directory: Path, tag: str, commit: str) -> dict:
    excluded = {"SHA256SUMS.txt", "RELEASE_MANIFEST.json"}
    files = sorted(
        (path for path in directory.iterdir() if path.is_file() and path.name not in excluded),
        key=lambda path: path.name,
    )
    return {
        "schema_version": "1.0.0",
        "tag": tag,
        "commit": commit,
        "assets": [
            {
                "name": path.name,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
    }


def write_outputs(directory: Path, tag: str, commit: str) -> None:
    manifest = build_manifest(directory, tag, commit)
    checksums = "".join(
        f"{item['sha256']}  {item['name']}\n" for item in manifest["assets"]
    )
    (directory / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    (directory / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    write_outputs(args.directory, args.tag, args.commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
