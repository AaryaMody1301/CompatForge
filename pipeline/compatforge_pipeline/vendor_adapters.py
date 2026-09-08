"""Source-specific vendor adapters and review-only semantic change reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPORT_VERSION = 1
MAX_SOURCE_BYTES = 2 * 1024 * 1024
USER_AGENT = "CompatForge-vendor-review/1.0"

FTDI_VCP_URL = "https://ftdichip.com/drivers/vcp-drivers/"
SALEAE_SUPPORTED_OS_URL = (
    "https://www.saleae.com/support/logic-software/download-and-installation/"
    "supported-operating-systems"
)


@dataclass(frozen=True, slots=True)
class VendorAdapter:
    name: str
    source_url: str
    allowed_host: str
    extractor: Callable[[str], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class FetchResult:
    body: bytes
    final_url: str
    etag: str | None
    last_modified: str | None
    content_type: str | None


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.casefold() in {"script", "style", "noscript"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


def _canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a timezone: {value}")
    return parsed.astimezone(UTC)


def _html_to_text(document: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(document)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def _segment_after(text: str, marker: str, *, length: int) -> str:
    index = text.casefold().find(marker.casefold())
    if index < 0:
        raise ValueError(f"source did not contain expected marker: {marker}")
    return text[index : index + length]


def _required_match(pattern: str, text: str, *, label: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"source did not contain expected {label}")
    return match.group(1)


def extract_ftdi_vcp(document: str) -> dict[str, Any]:
    """Extract the reviewed FTDI Windows VCP facts used by CompatForge."""
    text = _html_to_text(document)
    desktop = _segment_after(text, "Windows (Desktop)", length=1800)
    universal = _segment_after(text, "Windows (Universal)", length=1200)

    release_date = _required_match(
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        desktop,
        label="Windows Desktop release date",
    )
    x64_version = _required_match(
        r"\b(\d+\.\d+\.\d+\.\d+)\b",
        desktop,
        label="Windows Desktop x64 version",
    )
    arm64_version = _required_match(
        r"\b(\d+\.\d+\.\d+\.\d+A)\b",
        desktop,
        label="Windows Desktop ARM64 version",
    )
    universal_arm64_version = _required_match(
        r"\b(\d+\.\d+\.\d+\.\d+UA)\b",
        universal,
        label="Windows Universal ARM64 version",
    )
    lowered = text.casefold()
    installer_arm64_note = (
        "installer is not available for arm64" in lowered
        or "setup executable (non-arm64)" in lowered
    )
    if not installer_arm64_note:
        raise ValueError("source did not contain the reviewed ARM64 installer limitation")

    return {
        "installer_arm64_note": True,
        "windows_desktop_arm64_version": arm64_version,
        "windows_desktop_release_date": release_date,
        "windows_desktop_x64_version": x64_version,
        "windows_universal_arm64_version": universal_arm64_version,
    }


def extract_saleae_supported_os(document: str) -> dict[str, Any]:
    """Extract Saleae's general Logic 2 supported-OS architecture declarations."""
    text = _html_to_text(document)
    windows = bool(re.search(r"Windows\s*10\s*&\s*11\s*\(x64\)", text, re.IGNORECASE))
    macos = bool(
        re.search(
            r"macOS\s*12\s*Monterey\+\s*\(Intel\s*/\s*Apple\s+silicon\)",
            text,
            re.IGNORECASE,
        )
    )
    ubuntu = bool(re.search(r"Ubuntu\s*20\.04\+\s*\(64-bit\)", text, re.IGNORECASE))
    if not windows:
        raise ValueError("source did not contain the reviewed Windows 10/11 x64 declaration")
    if not macos:
        raise ValueError("source did not contain the reviewed macOS Intel/Apple silicon declaration")
    if not ubuntu:
        raise ValueError("source did not contain the reviewed Ubuntu 64-bit declaration")

    return {
        "macos_apple_silicon_declared": True,
        "ubuntu_64_bit_declared": True,
        "windows_architectures": ["x64"],
        "windows_versions": ["10", "11"],
    }


ADAPTERS: dict[str, VendorAdapter] = {
    "ftdi_vcp": VendorAdapter(
        name="ftdi_vcp",
        source_url=FTDI_VCP_URL,
        allowed_host="ftdichip.com",
        extractor=extract_ftdi_vcp,
    ),
    "saleae_supported_os": VendorAdapter(
        name="saleae_supported_os",
        source_url=SALEAE_SUPPORTED_OS_URL,
        allowed_host="www.saleae.com",
        extractor=extract_saleae_supported_os,
    ),
}


def _validate_source_url(adapter: VendorAdapter, url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"{adapter.name}: source must use HTTPS")
    if parsed.hostname != adapter.allowed_host:
        raise ValueError(
            f"{adapter.name}: final host {parsed.hostname!r} is outside permitted host "
            f"{adapter.allowed_host!r}"
        )


def fetch_source(adapter: VendorAdapter, *, timeout_seconds: float) -> FetchResult:
    """Fetch one explicitly permitted vendor source with a bounded response size."""
    _validate_source_url(adapter, adapter.source_url)
    request = urllib.request.Request(adapter.source_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            _validate_source_url(adapter, final_url)
            body = response.read(MAX_SOURCE_BYTES + 1)
            if len(body) > MAX_SOURCE_BYTES:
                raise ValueError(f"{adapter.name}: response exceeded {MAX_SOURCE_BYTES} bytes")
            return FetchResult(
                body=body,
                final_url=final_url,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                content_type=response.headers.get("Content-Type"),
            )
    except urllib.error.HTTPError as exc:
        raise ValueError(f"{adapter.name}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"{adapter.name}: source fetch failed: {type(exc).__name__}") from exc


def snapshot_from_html(
    adapter_name: str,
    document: str,
    *,
    checked_at: str,
    final_url: str | None = None,
    body_sha256: str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
) -> dict[str, Any]:
    """Build one semantic source snapshot from supplied HTML."""
    adapter = ADAPTERS[adapter_name]
    checked_at_dt = _parse_timestamp(checked_at)
    effective_url = final_url or adapter.source_url
    _validate_source_url(adapter, effective_url)
    facts = adapter.extractor(document)
    return {
        "adapter": adapter.name,
        "source_url": adapter.source_url,
        "final_url": effective_url,
        "checked_at": checked_at_dt.isoformat().replace("+00:00", "Z"),
        "facts": facts,
        "semantic_sha256": _canonical_sha256(facts),
        "body_sha256": body_sha256,
        "etag": etag,
        "last_modified": last_modified,
    }


def build_live_snapshot(
    *,
    adapter_names: list[str],
    checked_at: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Fetch permitted sources and emit semantic review snapshots."""
    names = sorted(set(adapter_names or ADAPTERS))
    unknown = [name for name in names if name not in ADAPTERS]
    if unknown:
        raise ValueError(f"unknown vendor adapters: {', '.join(unknown)}")

    sources = []
    for name in names:
        adapter = ADAPTERS[name]
        fetched = fetch_source(adapter, timeout_seconds=timeout_seconds)
        charset = "utf-8"
        if fetched.content_type:
            match = re.search(r"charset=([^;\s]+)", fetched.content_type, re.IGNORECASE)
            if match:
                charset = match.group(1).strip("\"'")
        document = fetched.body.decode(charset, errors="replace")
        sources.append(
            snapshot_from_html(
                name,
                document,
                checked_at=checked_at,
                final_url=fetched.final_url,
                body_sha256=hashlib.sha256(fetched.body).hexdigest(),
                etag=fetched.etag,
                last_modified=fetched.last_modified,
            )
        )

    checked_at_dt = _parse_timestamp(checked_at)
    return {
        "report_version": REPORT_VERSION,
        "checked_at": checked_at_dt.isoformat().replace("+00:00", "Z"),
        "sources": sources,
    }


def _load_baseline(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        raise ValueError(f"{path}: baseline facts must be an object")
    expected_sha = _canonical_sha256(facts)
    if payload.get("semantic_sha256") != expected_sha:
        raise ValueError(f"{path}: baseline semantic SHA-256 does not match facts")
    return payload


def build_change_report(*, snapshot: dict[str, Any], baseline_dir: Path) -> dict[str, Any]:
    """Compare live semantic facts with reviewed baselines without mutating evidence."""
    changes = []
    for current in sorted(snapshot["sources"], key=lambda item: item["adapter"]):
        baseline_path = baseline_dir / f"{current['adapter']}.json"
        if not baseline_path.exists():
            changes.append(
                {
                    "adapter": current["adapter"],
                    "source_url": current["source_url"],
                    "status": "missing_baseline",
                    "changed_fields": sorted(current["facts"]),
                    "baseline_semantic_sha256": None,
                    "current_semantic_sha256": current["semantic_sha256"],
                    "baseline_facts": None,
                    "current_facts": current["facts"],
                }
            )
            continue

        baseline = _load_baseline(baseline_path)
        keys = sorted(set(baseline["facts"]) | set(current["facts"]))
        changed_fields = [
            key for key in keys if baseline["facts"].get(key) != current["facts"].get(key)
        ]
        changes.append(
            {
                "adapter": current["adapter"],
                "source_url": current["source_url"],
                "status": "changed" if changed_fields else "unchanged",
                "changed_fields": changed_fields,
                "baseline_semantic_sha256": baseline["semantic_sha256"],
                "current_semantic_sha256": current["semantic_sha256"],
                "baseline_facts": baseline["facts"],
                "current_facts": current["facts"],
            }
        )

    summary = {
        "total": len(changes),
        "unchanged": sum(item["status"] == "unchanged" for item in changes),
        "changed": sum(item["status"] == "changed" for item in changes),
        "missing_baseline": sum(item["status"] == "missing_baseline" for item in changes),
    }
    report = {
        "report_version": REPORT_VERSION,
        "checked_at": snapshot["checked_at"],
        "summary": summary,
        "changes": changes,
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


def render_change_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Vendor source semantic changes",
        "",
        f"Checked at `{report['checked_at']}`.",
        "",
        f"- Sources: **{summary['total']}**",
        f"- Unchanged: **{summary['unchanged']}**",
        f"- Changed: **{summary['changed']}**",
        f"- Missing baseline: **{summary['missing_baseline']}**",
        "",
        "| Adapter | Status | Changed fields |",
        "| --- | --- | --- |",
    ]
    for item in report["changes"]:
        fields = ", ".join(f"`{field}`" for field in item["changed_fields"]) or "none"
        lines.append(f"| `{item['adapter']}` | {item['status']} | {fields} |")
    lines.extend(
        [
            "",
            f"Report SHA-256: `{report['report_sha256']}`",
            "",
            "This is a review candidate only. It never rewrites canonical evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser("snapshot", help="fetch permitted vendor semantic snapshots")
    snapshot.add_argument("--adapter", action="append", choices=sorted(ADAPTERS))
    snapshot.add_argument("--checked-at", required=True)
    snapshot.add_argument("--timeout-seconds", type=float, default=20.0)
    snapshot.add_argument("--output", type=Path, required=True)

    compare = commands.add_parser("compare", help="compare live semantic facts with baselines")
    compare.add_argument("--snapshot", type=Path, required=True)
    compare.add_argument("--baselines", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    compare.add_argument("--summary", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "snapshot":
        payload = build_live_snapshot(
            adapter_names=args.adapter or [],
            checked_at=args.checked_at,
            timeout_seconds=args.timeout_seconds,
        )
        _write_json(args.output, payload)
        return 0

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    report = build_change_report(snapshot=snapshot, baseline_dir=args.baselines)
    _write_json(args.output, report)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(render_change_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
