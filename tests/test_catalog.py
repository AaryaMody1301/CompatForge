from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
CURATED_PATH = ROOT / "data" / "catalog" / "curated-devices.json"
PUBLISHED_PATH = ROOT / "data" / "catalog" / "usb-device-catalog.json"
USB_ID = re.compile(r"^usb:[0-9A-F]{4}:[0-9A-F]{4}$")
HEX4 = re.compile(r"^[0-9A-F]{4}$")


def _curated() -> list[dict]:
    payload = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def _published() -> dict:
    payload = json.loads(PUBLISHED_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _published_ids(payload: dict) -> set[str]:
    return {
        f"usb:{vendor_id}:{product_id}"
        for vendor_id, _vendor_name, products in payload["vendors"]
        for product_id, _product_name in products
    }


def test_published_usb_catalog_is_broad_canonical_and_provenanced() -> None:
    payload = _published()
    ids = _published_ids(payload)

    assert payload["schema_version"] == 1
    assert payload["counts"]["devices"] == len(ids)
    assert payload["counts"]["vendors"] == len(payload["vendors"])
    assert len(ids) >= 20_000
    assert all(USB_ID.fullmatch(device_id) for device_id in ids)
    assert len(payload["source"]["sha256"]) == 64
    assert payload["source"]["homepage"] == "https://usb-ids.gowdy.us/"
    assert payload["source"]["license"] == "GPL-2.0-or-later OR BSD-3-Clause"
    assert payload["source"]["parser_version"] == "2"
    assert payload["source"]["version"] == "2026.06.26"
    assert payload["source"]["snapshot_date"] == "2026-06-26"

    vendor_ids = [vendor_id for vendor_id, _vendor_name, _products in payload["vendors"]]
    assert vendor_ids == sorted(vendor_ids)
    assert len(vendor_ids) == len(set(vendor_ids))
    assert all(HEX4.fullmatch(vendor_id) for vendor_id in vendor_ids)

    for _vendor_id, vendor_name, products in payload["vendors"]:
        assert vendor_name.strip()
        product_ids = [product_id for product_id, _product_name in products]
        assert product_ids == sorted(product_ids)
        assert len(product_ids) == len(set(product_ids))
        assert all(HEX4.fullmatch(product_id) for product_id in product_ids)
        assert all(product_name.strip() for _product_id, product_name in products)


def test_curated_metadata_is_unique_canonical_and_published() -> None:
    catalog = _curated()
    ids = [item["id"] for item in catalog]
    slugs = [item["slug"] for item in catalog]
    published_ids = _published_ids(_published())

    assert len(catalog) >= 10
    assert len(ids) == len(set(ids))
    assert len(slugs) == len(set(slugs))
    assert all(USB_ID.fullmatch(device_id) for device_id in ids)
    assert all(str(item["identity_source"]).startswith("https://") for item in catalog)
    assert all(item["aliases"] for item in catalog)
    assert set(ids) <= published_ids


def test_every_reviewed_evidence_device_exists_in_full_catalog() -> None:
    published_ids = _published_ids(_published())
    evidence_paths = [
        *sorted((ROOT / "data" / "evidence" / "observations").glob("*.json")),
        *sorted((ROOT / "data" / "evidence" / "vendor").glob("*.json")),
    ]
    evidence_ids = {
        json.loads(path.read_text(encoding="utf-8"))["device_id"] for path in evidence_paths
    }

    assert evidence_ids <= published_ids
