from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def test_packaged_schemas_match_public_contracts() -> None:
    public_dir = Path("schemas")
    packaged_dir = files("compatforge_pipeline").joinpath("resources").joinpath("schemas")
    public_names = sorted(path.name for path in public_dir.glob("*.json"))
    packaged_names = sorted(item.name for item in packaged_dir.iterdir() if item.name.endswith(".json"))

    assert packaged_names == public_names
    for name in public_names:
        expected = (public_dir / name).read_text(encoding="utf-8")
        actual = packaged_dir.joinpath(name).read_text(encoding="utf-8")
        assert actual == expected, f"packaged schema drifted: {name}"
