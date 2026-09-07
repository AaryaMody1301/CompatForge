import pytest
from compatforge_pipeline.identity import normalize_usb_hex, usb_device_id


def test_normalize_usb_hex_accepts_common_forms() -> None:
    assert normalize_usb_hex("403") == "0403"
    assert normalize_usb_hex("0x0403") == "0403"
    assert normalize_usb_hex("ea60") == "EA60"


@pytest.mark.parametrize("value", ["", "10000", "GGGG", "12-34"])
def test_normalize_usb_hex_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_usb_hex(value)


def test_usb_device_id_is_deterministic() -> None:
    assert usb_device_id("0x0403", "6001") == "usb:0403:6001"
