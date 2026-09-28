"""Create a cross-platform CompatForge CLI release archive."""

from __future__ import annotations

import argparse
import gzip
import io
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def package_release(binary: Path, asset_name: str, output_dir: Path) -> Path:
    if not binary.is_file():
        raise FileNotFoundError(binary)

    output_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(
        (
            binary,
            REPO_ROOT / "LICENSE",
            REPO_ROOT / "THIRD_PARTY_NOTICES.md",
            REPO_ROOT / "docs" / "CLI_RELEASE.md",
        ),
        key=lambda path: path.name,
    )
    if any(path.is_symlink() or not path.is_file() for path in sources):
        raise ValueError("CLI release inputs must be ordinary files")

    archive = output_dir / asset_name
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for path in sources:
                info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100755 if path == binary else 0o100644) << 16
                handle.writestr(info, path.read_bytes())
    elif archive.name.endswith(".tar.gz"):
        with (
            archive.open("wb") as raw,
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
            tarfile.open(fileobj=compressed, mode="w") as handle,
        ):
            for path in sources:
                data = path.read_bytes()
                info = tarfile.TarInfo(path.name)
                info.size = len(data)
                info.mode = 0o755 if path == binary else 0o644
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                handle.addfile(info, io.BytesIO(data))
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
