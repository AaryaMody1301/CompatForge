"""Parser and source acquisition helpers for the upstream usb.ids registry."""

from __future__ import annotations

import gzip
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from compatforge_pipeline.identity import normalize_usb_hex, usb_device_id

USB_IDS_URL = "https://usb-ids.gowdy.us/usb.ids.gz"
USB_IDS_HOMEPAGE = "https://usb-ids.gowdy.us/"
USB_IDS_LICENSE = "GPL-2.0-or-later OR BSD-3-Clause"
USB_IDS_PARSER_VERSION = "2"
USER_AGENT = "CompatForge/0.2 (+https://github.com/AaryaMody1301/CompatForge)"

_VENDOR_LINE = re.compile(r"^([0-9A-Fa-f]{4})\s+(.+?)\s*$")
_DEVICE_LINE = re.compile(r"^\t([0-9A-Fa-f]{4})\s+(.+?)\s*$")


class UsbIdsParseError(ValueError):
    """Raised when usb.ids violates identity assumptions required by CompatForge."""


@dataclass(frozen=True, slots=True)
class UsbVendor:
    vendor_id: str
    vendor_name: str
    source_line: int


@dataclass(frozen=True, slots=True)
class UsbDevice:
    device_id: str
    vendor_id: str
    product_id: str
    product_name: str
    source_line: int


@dataclass(frozen=True, slots=True)
class DownloadedSource:
    content: bytes
    source_url: str
    upstream_last_modified: str | None
    upstream_etag: str | None


def download_usb_ids(url: str = USB_IDS_URL, *, timeout: int = 30) -> DownloadedSource:
    """Download the compressed upstream snapshot using an identifying User-Agent."""
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
        last_modified = response.headers.get("Last-Modified")
        etag = response.headers.get("ETag")
    if payload.startswith(b"\x1f\x8b") or url.endswith(".gz"):
        try:
            payload = gzip.decompress(payload)
        except OSError as exc:
            raise UsbIdsParseError("Downloaded usb.ids payload is not valid gzip") from exc
    _decode_source(payload)
    return DownloadedSource(payload, url, last_modified, etag)


def load_usb_ids(path: Path) -> DownloadedSource:
    payload = path.read_bytes()
    if payload.startswith(b"\x1f\x8b") or path.suffix == ".gz":
        payload = gzip.decompress(payload)
    _decode_source(payload)
    return DownloadedSource(payload, path.resolve().as_uri(), None, None)


def parse_usb_ids(content: bytes | str) -> tuple[list[UsbVendor], list[UsbDevice]]:
    """Parse vendor/product identities while ignoring class and nested interface sections."""
    text = _decode_source(content) if isinstance(content, bytes) else content
    vendors: list[UsbVendor] = []
    devices: list[UsbDevice] = []
    seen_vendors: set[str] = set()
    seen_devices: set[str] = set()
    current_vendor: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line or raw_line.startswith("#"):
            continue
        if raw_line.startswith("\t\t"):
            continue
        device_match = _DEVICE_LINE.fullmatch(raw_line)
        if device_match and current_vendor is not None:
            product_id = normalize_usb_hex(device_match.group(1))
            canonical_id = usb_device_id(current_vendor, product_id)
            if canonical_id in seen_devices:
                raise UsbIdsParseError(f"Duplicate USB device {canonical_id} at line {line_number}")
            seen_devices.add(canonical_id)
            devices.append(
                UsbDevice(
                    canonical_id,
                    current_vendor,
                    product_id,
                    device_match.group(2).strip(),
                    line_number,
                )
            )
            continue
        if raw_line[0].isspace():
            continue
        vendor_match = _VENDOR_LINE.fullmatch(raw_line)
        if vendor_match:
            vendor_id = normalize_usb_hex(vendor_match.group(1))
            if vendor_id in seen_vendors:
                raise UsbIdsParseError(f"Duplicate USB vendor {vendor_id} at line {line_number}")
            seen_vendors.add(vendor_id)
            vendors.append(UsbVendor(vendor_id, vendor_match.group(2).strip(), line_number))
            current_vendor = vendor_id
            continue
        current_vendor = None

    if not vendors or not devices:
        raise UsbIdsParseError("usb.ids produced no vendor/product identities")
    return vendors, devices


def source_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _decode_source(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("iso-8859-1")
