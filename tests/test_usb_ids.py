from pathlib import Path

import pytest
from compatforge_pipeline.usb_ids import UsbIdsParseError, parse_usb_ids

FIXTURE = Path(__file__).parent / "fixtures" / "usb.ids"


def test_parser_extracts_only_vendor_product_identities() -> None:
    vendors, devices = parse_usb_ids(FIXTURE.read_bytes())
    assert [(row.vendor_id, row.vendor_name) for row in vendors] == [
        ("1234", "Example Instruments"),
        ("ABCD", "Demo Labs"),
    ]
    assert [row.device_id for row in devices] == [
        "usb:1234:0001",
        "usb:1234:0002",
        "usb:ABCD:00FF",
    ]
    assert all("Nested" not in row.product_name for row in devices)


def test_parser_rejects_duplicate_device_identity() -> None:
    content = "1234  Vendor\n\t0001  First\n\t0001  Duplicate\n"
    with pytest.raises(UsbIdsParseError, match="Duplicate USB device"):
        parse_usb_ids(content)
