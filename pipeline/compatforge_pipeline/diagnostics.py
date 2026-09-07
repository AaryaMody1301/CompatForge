"""Privacy-minimized local diagnostic manifest collection."""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
from contextlib import suppress
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .contracts import validate_document
from .identity import normalize_usb_hex, usb_device_id

_DIAGNOSTIC_SCHEMA_VERSION = "1.0.0"
_DEVICE_ID_RE = re.compile(r"^usb:([0-9A-Fa-f]{1,4}):([0-9A-Fa-f]{1,4})$")
_MAC_USB_HEX_RE = re.compile(r"0x([0-9A-Fa-f]{4})")


class DiagnosticCollectionError(RuntimeError):
    """Raised when an OS collector cannot safely complete."""


def _agent_version() -> str:
    try:
        return version("compatforge-hw-pipeline")
    except PackageNotFoundError:
        return "0+unknown"


def normalize_architecture(value: str) -> str:
    """Normalize common machine names into CompatForge architecture values."""

    candidate = value.strip().lower()
    if candidate in {"x86_64", "amd64", "x64"}:
        return "x86_64"
    if candidate in {"arm64", "aarch64"}:
        return "arm64"
    return "unknown"


def parse_usb_device_id(value: str) -> tuple[str, str, str]:
    """Return canonical device ID, VID and PID from a CompatForge USB ID."""

    match = _DEVICE_ID_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("device must use the form usb:VID:PID")
    vid = normalize_usb_hex(match.group(1))
    pid = normalize_usb_hex(match.group(2))
    return usb_device_id(vid, pid), vid, pid


def _run_text(command: list[str], *, timeout: int = 15) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise DiagnosticCollectionError("local OS collector failed") from exc
    return completed.stdout.strip()


def _run_json(command: list[str], *, timeout: int = 15) -> Any:
    raw = _run_text(command, timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DiagnosticCollectionError("local OS collector returned invalid JSON") from exc


def _safe_read(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _powershell_executable() -> str:
    executable = (
        shutil.which("powershell.exe")
        or shutil.which("powershell")
        or shutil.which("pwsh")
    )
    if executable is None:
        raise DiagnosticCollectionError("PowerShell is unavailable")
    return executable


def _collect_windows_platform_host() -> tuple[dict[str, str], dict[str, str], list[str]]:
    script = r"""
$ErrorActionPreference = 'Stop'
$computer = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
  manufacturer = [string]$computer.Manufacturer
  model = [string]$computer.Model
  os_caption = [string]$os.Caption
  os_version = [string]$os.Version
  os_build = [string]$os.BuildNumber
} | ConvertTo-Json -Compress
"""
    warnings: list[str] = []
    host: dict[str, str] = {}
    os_name = "Windows"
    os_version = platform.version() or "unknown"
    os_build: str | None = None
    try:
        payload = _run_json(
            [_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", script]
        )
        if isinstance(payload, dict):
            manufacturer = str(payload.get("manufacturer") or "").strip()
            model = str(payload.get("model") or "").strip()
            caption = str(payload.get("os_caption") or "").strip()
            raw_version = str(payload.get("os_version") or "").strip()
            build = str(payload.get("os_build") or "").strip()
            if manufacturer:
                host["manufacturer"] = manufacturer
            if model:
                host["model"] = model
            if caption:
                os_name = caption
            if "Windows 11" in caption:
                os_version = "11"
            elif raw_version:
                os_version = raw_version
            if build:
                os_build = build
    except DiagnosticCollectionError:
        warnings.append(
            "Windows host details were unavailable; platform fallback values were used."
        )

    platform_record = {
        "os_family": "windows",
        "os_name": os_name,
        "os_version": os_version,
        "architecture": normalize_architecture(platform.machine()),
    }
    if os_build:
        platform_record["os_build"] = os_build
    return platform_record, host, warnings


def _collect_macos_platform_host() -> tuple[dict[str, str], dict[str, str], list[str]]:
    warnings: list[str] = []
    host: dict[str, str] = {"manufacturer": "Apple"}
    model: str | None = None
    sysctl = shutil.which("sysctl") or "/usr/sbin/sysctl"
    try:
        model = _run_text([sysctl, "-n", "hw.model"], timeout=5)
    except DiagnosticCollectionError:
        warnings.append("Mac model identifier was unavailable.")
    if model:
        host["model"] = model

    os_version = platform.mac_ver()[0] or "unknown"
    return (
        {
            "os_family": "macos",
            "os_name": "macOS",
            "os_version": os_version,
            "architecture": normalize_architecture(platform.machine()),
        },
        host,
        warnings,
    )


def _collect_linux_platform_host() -> tuple[dict[str, str], dict[str, str], list[str]]:
    warnings: list[str] = []
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        release = {}
        warnings.append("Linux distribution metadata was unavailable.")

    distro_id = release.get("ID", "").strip().lower()
    os_family = "ubuntu" if distro_id == "ubuntu" else "linux"
    os_name = release.get("PRETTY_NAME") or release.get("NAME") or "Linux"
    os_version = release.get("VERSION_ID") or platform.release() or "unknown"

    host: dict[str, str] = {}
    manufacturer = _safe_read(Path("/sys/devices/virtual/dmi/id/sys_vendor"))
    model = _safe_read(Path("/sys/devices/virtual/dmi/id/product_name"))
    if manufacturer:
        host["manufacturer"] = manufacturer
    if model:
        host["model"] = model

    return (
        {
            "os_family": os_family,
            "os_name": os_name,
            "os_version": os_version,
            "architecture": normalize_architecture(platform.machine()),
        },
        host,
        warnings,
    )


def _collect_platform_host(
    system_name: str | None = None,
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    system = (system_name or platform.system()).lower()
    if system == "windows":
        return _collect_windows_platform_host()
    if system == "darwin":
        return _collect_macos_platform_host()
    if system == "linux":
        return _collect_linux_platform_host()
    return (
        {
            "os_family": "unknown",
            "os_name": platform.system() or "Unknown",
            "os_version": platform.release() or "unknown",
            "architecture": normalize_architecture(platform.machine()),
        },
        {},
        ["This operating system does not yet have a dedicated host collector."],
    )


def _dedupe_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rendered: dict[str, dict[str, Any]] = {}
    for item in matches:
        key = json.dumps(item, sort_keys=True, separators=(",", ":"))
        rendered[key] = item
    return [rendered[key] for key in sorted(rendered)]


def _parse_windows_usb_payload(
    payload: Any,
    target_id: str,
) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict):
        raise DiagnosticCollectionError("Windows USB collector returned an invalid payload")
    devices = payload.get("devices", [])
    if isinstance(devices, dict):
        devices = [devices]
    if not isinstance(devices, list):
        raise DiagnosticCollectionError("Windows USB collector returned an invalid device list")

    matches: list[dict[str, Any]] = []
    raw_count = 0
    for item in devices:
        if not isinstance(item, dict):
            continue
        try:
            device_id = usb_device_id(
                str(item.get("vendor_id", "")),
                str(item.get("product_id", "")),
            )
        except (TypeError, ValueError):
            continue
        if device_id != target_id:
            continue
        raw_count += 1
        safe: dict[str, Any] = {"device_id": device_id, "connection_path": "unspecified"}
        status = str(item.get("status") or "").strip()
        if status:
            safe["status"] = status
        matches.append(safe)
    return _dedupe_matches(matches), raw_count


def _collect_windows_target(vid: str, pid: str) -> tuple[list[dict[str, Any]], int]:
    script = r"""
$ErrorActionPreference = 'Stop'
$vid = '__VID__'
$pid = '__PID__'
$results = @()
Get-PnpDevice -PresentOnly | ForEach-Object {
  $instance = [string]$_.InstanceId
  if ($instance -match '^USB\\VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})') {
    $foundVid = $Matches[1].ToUpperInvariant()
    $foundPid = $Matches[2].ToUpperInvariant()
    if ($foundVid -eq $vid -and $foundPid -eq $pid) {
      $results += [pscustomobject]@{
        vendor_id = $foundVid
        product_id = $foundPid
        status = [string]$_.Status
      }
    }
  }
}
[pscustomobject]@{ devices = @($results) } | ConvertTo-Json -Compress -Depth 4
""".replace("__VID__", vid).replace("__PID__", pid)
    payload = _run_json(
        [_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=20,
    )
    return _parse_windows_usb_payload(payload, usb_device_id(vid, pid))


def _extract_macos_usb_hex(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _MAC_USB_HEX_RE.search(value)
    return match.group(1).upper() if match else None


def _parse_macos_usb_payload(
    payload: Any,
    target_id: str,
) -> tuple[list[dict[str, Any]], int]:
    matches: list[dict[str, Any]] = []
    raw_count = 0

    def visit(node: Any) -> None:
        nonlocal raw_count
        if isinstance(node, dict):
            vid = _extract_macos_usb_hex(node.get("vendor_id"))
            pid = _extract_macos_usb_hex(node.get("product_id"))
            if vid and pid and usb_device_id(vid, pid) == target_id:
                raw_count += 1
                matches.append({"device_id": target_id, "connection_path": "unspecified"})
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(payload)
    return _dedupe_matches(matches), raw_count


def _collect_macos_target(vid: str, pid: str) -> tuple[list[dict[str, Any]], int]:
    profiler = shutil.which("system_profiler") or "/usr/sbin/system_profiler"
    payload = _run_json(
        [profiler, "SPUSBDataType", "-json", "-detailLevel", "mini"],
        timeout=25,
    )
    return _parse_macos_usb_payload(payload, usb_device_id(vid, pid))


def _collect_linux_target(
    vid: str,
    pid: str,
    *,
    sysfs_root: Path = Path("/sys/bus/usb/devices"),
) -> tuple[list[dict[str, Any]], int]:
    if not sysfs_root.is_dir():
        raise DiagnosticCollectionError("Linux USB sysfs is unavailable")

    matches: list[dict[str, Any]] = []
    raw_count = 0
    for device_dir in sorted(sysfs_root.iterdir(), key=lambda item: item.name):
        if ":" in device_dir.name:
            continue
        found_vid = _safe_read(device_dir / "idVendor")
        found_pid = _safe_read(device_dir / "idProduct")
        if not found_vid or not found_pid:
            continue
        try:
            normalized_vid = normalize_usb_hex(found_vid)
            normalized_pid = normalize_usb_hex(found_pid)
        except ValueError:
            continue
        if normalized_vid != vid or normalized_pid != pid:
            continue

        raw_count += 1
        topology_name = device_dir.name.split(":", maxsplit=1)[0]
        connection_path = "usb_hub" if "." in topology_name else "direct_port"
        safe: dict[str, Any] = {
            "device_id": usb_device_id(vid, pid),
            "connection_path": connection_path,
            "status": "present",
        }
        speed = _safe_read(device_dir / "speed")
        if speed:
            with suppress(ValueError):
                safe["speed_mbps"] = float(speed)
        matches.append(safe)
    return _dedupe_matches(matches), raw_count


def _collect_target(
    system_name: str,
    vid: str,
    pid: str,
) -> tuple[list[dict[str, Any]], int]:
    system = system_name.lower()
    if system == "windows":
        return _collect_windows_target(vid, pid)
    if system == "darwin":
        return _collect_macos_target(vid, pid)
    if system == "linux":
        return _collect_linux_target(vid, pid)
    raise DiagnosticCollectionError("target USB collection is unsupported on this operating system")


def collect_diagnostic(
    device_id: str | None = None,
    *,
    system_name: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Collect a schema-valid local diagnostic manifest with a strict privacy allowlist."""

    effective_system = system_name or platform.system()
    platform_record, host, warnings = _collect_platform_host(effective_system)
    manifest: dict[str, Any] = {
        "record_type": "diagnostic_manifest",
        "schema_version": _DIAGNOSTIC_SCHEMA_VERSION,
        "agent": {"name": "compatforge-diagnose", "version": _agent_version()},
        "generated_at": generated_at
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "platform": platform_record,
        "host": host,
        "privacy": {
            "collection_mode": "local_only",
            "scope": "target_device_only" if device_id else "host_only",
            "serial_numbers_in_manifest": False,
            "network_identifiers_in_manifest": False,
            "unrelated_usb_devices_in_manifest": False,
            "automatic_upload": False,
        },
        "warnings": warnings,
    }

    if device_id:
        canonical_id, vid, pid = parse_usb_device_id(device_id)
        try:
            matches, match_count = _collect_target(effective_system, vid, pid)
            manifest["target"] = {
                "requested_device_id": canonical_id,
                "collection_status": "collected",
                "present": match_count > 0,
                "match_count": match_count,
                "matches": matches,
            }
        except DiagnosticCollectionError:
            manifest["target"] = {
                "requested_device_id": canonical_id,
                "collection_status": "unavailable",
                "present": None,
                "match_count": 0,
                "matches": [],
            }
            manifest["warnings"].append("Target USB collection was unavailable on this host.")

    manifest["warnings"] = sorted(set(manifest["warnings"]))
    validate_document(manifest, source="diagnostic manifest")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect a privacy-minimized local CompatForge diagnostic manifest"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--device", help="target canonical USB device ID, for example usb:0403:6001")
    mode.add_argument("--host-only", action="store_true", help="collect only host/OS metadata")
    parser.add_argument("--output", default="-", help="output JSON path, or - for stdout")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = collect_diagnostic(args.device if not args.host_only else None)
    except (ValueError, DiagnosticCollectionError) as exc:
        print(f"diagnostic failed: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        sys.stdout.write(rendered)
        return 0

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    print(f"wrote diagnostic manifest to {destination}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
