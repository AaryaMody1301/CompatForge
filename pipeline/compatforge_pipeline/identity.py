"""Deterministic hardware identity helpers."""

from __future__ import annotations

import re

_HEX_4 = re.compile(r"^[0-9A-F]{4}$")


def normalize_usb_hex(value: str) -> str:
    """Normalize a USB VID/PID into four uppercase hexadecimal characters.

    Accepted inputs include values such as ``0403``, ``0x0403`` and ``403``.
    Values outside the unsigned 16-bit USB identifier range are rejected.
    """

    if not isinstance(value, str):
        raise TypeError("USB identifiers must be strings")

    candidate = value.strip().upper()
    if candidate.startswith("0X"):
        candidate = candidate[2:]

    if not candidate or len(candidate) > 4 or not re.fullmatch(r"[0-9A-F]+", candidate):
        raise ValueError(f"Invalid USB identifier: {value!r}")

    normalized = f"{int(candidate, 16):04X}"
    if not _HEX_4.fullmatch(normalized):
        raise ValueError(f"Invalid USB identifier: {value!r}")
    return normalized


def usb_device_id(vendor_id: str, product_id: str) -> str:
    """Return the canonical Phase 1 USB device identity."""

    return f"usb:{normalize_usb_hex(vendor_id)}:{normalize_usb_hex(product_id)}"
