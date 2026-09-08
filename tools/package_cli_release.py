"""Create a cross-platform CompatForge CLI release archive."""

from __future__ import annotations

import argparse
import shutil
import tarfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def package_release(binary: Path, asset_name: str, output_dir: Path) -> Path:
    if not binary.is_file():
        raise FileNotFoundError(binary)

    output_dir.mkdir(parents=True, exist_ok=True)
    stage = output_dir / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()

    staged_binary = stage / binary.name
    shutil.copy2(binary, staged_binary)
    staged_binary.chmod(staged_binary.stat().st_mode | 0o111)
    for source in (
        REPO_ROOT / "LICENSE",
        REPO_ROOT / "THIRD_PARTY_NOTICES.md",
        REPO_ROOT / "docs" / "CLI_RELEASE.md",
    ):
        shutil.copy2(source, stage / source.name)

    archive = output_dir / asset_name
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for path in sorted(stage.iterdir(), key=lambda item: item.name):
                handle.write(path, arcname=path.name)
    elif archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "w:gz") as handle:
            for path in sorted(stage.iterdir(), key=lambda item: item.name):
                handle.add(path, arcname=path.name)
    else:
        raise ValueError("asset name must end in .zip or .tar.gz")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--asset-name", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("build/release"))
    args = parser.parse_args()
    archive = package_release(args.binary, args.asset_name, args.output_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
