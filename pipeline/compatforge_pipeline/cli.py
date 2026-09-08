"""Unified end-user CLI for the CompatForge hardware diagnostic release."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .contribution_handoff import ContributionHandoffError, prepare_contribution_handoff
from .diagnostics import DiagnosticCollectionError, collect_diagnostic
from .local_explain import LocalExplanationError, explain_diagnostic
from .local_snapshot import LocalSnapshotError, load_packaged_snapshot, snapshot_sha256


def _write_json(payload: dict[str, Any], destination: str) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if destination == "-":
        sys.stdout.write(rendered)
        return
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    print(f"wrote {payload['record_type']} to {path}", file=sys.stderr)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compatforge-hw",
        description="Local, privacy-minimized hardware compatibility diagnostics",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    diagnose = commands.add_parser("diagnose", help="collect a local diagnostic manifest")
    mode = diagnose.add_mutually_exclusive_group(required=True)
    mode.add_argument("--device", help="canonical USB device ID, for example usb:0403:6001")
    mode.add_argument("--host-only", action="store_true", help="collect only host/OS metadata")
    diagnose.add_argument("--output", default="-", help="output JSON path, or - for stdout")

    explain = commands.add_parser("explain", help="resolve a diagnostic against the local snapshot")
    explain.add_argument("--diagnostic", type=Path, required=True)
    explain.add_argument("--output", default="-", help="output JSON path, or - for stdout")

    commands.add_parser("snapshot-info", help="show packaged snapshot metadata")

    handoff = commands.add_parser(
        "prepare-contribution",
        help="export a local-only future-contribution handoff after explicit approval",
    )
    handoff.add_argument("--diagnostic", type=Path, required=True)
    handoff.add_argument("--explanation", type=Path, required=True)
    handoff.add_argument(
        "--approve-export",
        action="store_true",
        help="confirm that the generated handoff may be written locally for inspection",
    )
    handoff.add_argument("--output", required=True, help="destination JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "diagnose":
            manifest = collect_diagnostic(args.device if not args.host_only else None)
            _write_json(manifest, args.output)
            return 0

        if args.command == "explain":
            explanation = explain_diagnostic(_load_json(args.diagnostic))
            _write_json(explanation, args.output)
            return 0

        if args.command == "snapshot-info":
            snapshot = load_packaged_snapshot()
            print(
                json.dumps(
                    {
                        "format_version": snapshot["format_version"],
                        "observation_count": snapshot["observation_count"],
                        "support_statement_count": snapshot["support_statement_count"],
                        "sha256": snapshot_sha256(snapshot),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        handoff = prepare_contribution_handoff(
            _load_json(args.diagnostic),
            _load_json(args.explanation),
            approved_export=args.approve_export,
        )
        _write_json(handoff, args.output)
        return 0
    except (
        ContributionHandoffError,
        DiagnosticCollectionError,
        LocalExplanationError,
        LocalSnapshotError,
        OSError,
        ValueError,
    ) as exc:
        print(f"compatforge-hw failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
