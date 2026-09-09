from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
CATALOG_PATH = ROOT / "data" / "catalog" / "release-preview-devices.json"
USB_ID = re.compile(r"^usb:[0-9A-F]{4}:[0-9A-F]{4}$")


def _catalog() -> list[dict]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def test_release_preview_catalog_is_unique_and_canonical() -> None:
    catalog = _catalog()
    ids = [item["id"] for item in catalog]
    slugs = [item["slug"] for item in catalog]

    assert len(catalog) >= 10
    assert len(ids) == len(set(ids))
    assert len(slugs) == len(set(slugs))
    assert all(USB_ID.fullmatch(device_id) for device_id in ids)
    assert all(str(item["identity_source"]).startswith("https://") for item in catalog)
    assert all(item["aliases"] for item in catalog)


def test_every_reviewed_evidence_device_exists_in_catalog() -> None:
    catalog_ids = {item["id"] for item in _catalog()}
    evidence_paths = [
        *sorted((ROOT / "data" / "evidence" / "observations").glob("*.json")),
        *sorted((ROOT / "data" / "evidence" / "vendor").glob("*.json")),
    ]
    evidence_ids = {
        json.loads(path.read_text(encoding="utf-8"))["device_id"] for path in evidence_paths
    }

    assert evidence_ids <= catalog_ids
