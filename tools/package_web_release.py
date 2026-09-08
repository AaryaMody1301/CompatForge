"""Package the Next.js build output into a deterministic tar.gz release artifact."""

from __future__ import annotations

import argparse
import gzip
import io
import tarfile
from pathlib import Path

EXCLUDED_PARTS = {"cache", "diagnostics"}


def _release_files(web_root: Path) -> list[tuple[Path, str]]:
    build_root = web_root / ".next"
    if not build_root.is_dir():
        raise FileNotFoundError(f"Next.js build output does not exist: {build_root}")

    files: list[tuple[Path, str]] = []
    for path in build_root.rglob("*"):
        relative = path.relative_to(web_root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"web release packaging refuses symlink: {relative.as_posix()}")
        if path.is_file():
            files.append((path, relative.as_posix()))

    for name in ("package.json", "package-lock.json", "next.config.ts"):
        path = web_root / name
        if not path.is_file():
            raise FileNotFoundError(f"required web release input does not exist: {path}")
        files.append((path, name))

    files.sort(key=lambda item: item[1])
    return files


def package_web_release(web_root: Path, output: Path) -> None:
    """Write a byte-stable archive for identical selected file contents."""

    web_root = web_root.resolve()
    files = _release_files(web_root)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for source, archive_name in files:
                    data = source.read_bytes()
                    info = tarfile.TarInfo(archive_name)
                    info.size = len(data)
                    info.mtime = 0
                    info.mode = 0o644
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    archive.addfile(info, io.BytesIO(data))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-root", type=Path, default=Path("apps/web"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package_web_release(args.web_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
