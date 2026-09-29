import hashlib
import os
import runpy
import tarfile
import zipfile
from pathlib import Path

import pytest

package_release = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "tools" / "package_cli_release.py")
)["package_release"]


@pytest.mark.parametrize("extension", ["zip", "tar.gz"])
def test_cli_release_archive_is_independent_of_input_mtime(
    tmp_path: Path, extension: str
) -> None:
    binary = tmp_path / "compatforge-hw"
    binary.write_bytes(b"deterministic executable")
    first = package_release(binary, f"first.{extension}", tmp_path / "output")
    before = hashlib.sha256(first.read_bytes()).hexdigest()
    assert (tmp_path / "output" / "stage" / binary.name).read_bytes() == binary.read_bytes()

    os.utime(binary, (1234567890, 1234567890))
    second = package_release(binary, f"second.{extension}", tmp_path / "output")
    assert hashlib.sha256(second.read_bytes()).hexdigest() == before

    if extension == "zip":
        with zipfile.ZipFile(second) as archive:
            assert archive.read(binary.name) == b"deterministic executable"
            assert archive.getinfo(binary.name).date_time == (1980, 1, 1, 0, 0, 0)
    else:
        with tarfile.open(second) as archive:
            entry = archive.getmember(binary.name)
            assert entry.mtime == 0
            assert entry.mode == 0o755
