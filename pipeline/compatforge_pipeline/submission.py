"""Deterministic helpers for community evidence submissions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import validate_document


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def payload_sha256(document: dict[str, Any]) -> str:
    """Hash the complete submission payload using canonical JSON."""

    validate_document(document)
    if document.get("record_type") != "community_evidence_submission":
        raise ValueError("payload_sha256 requires a community evidence submission")
    return hashlib.sha256(_canonical_bytes(document)).hexdigest()


def submission_fingerprint(document: dict[str, Any]) -> str:
    """Build a stable duplicate-candidate fingerprint from evidence semantics.

    Transport metadata such as the client submission ID and preparation time is
    intentionally excluded. The fingerprint is a moderation hint, not an
    automatic rejection rule.
    """

    validate_document(document)
    if document.get("record_type") != "community_evidence_submission":
        raise ValueError("submission_fingerprint requires a community evidence submission")

    semantic_payload = {
        "target_device_id": document["target_device_id"],
        "configuration": document["configuration"],
        "reproduction": document["reproduction"],
        "references": document["references"],
    }
    return hashlib.sha256(_canonical_bytes(semantic_payload)).hexdigest()


def _load_submission(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError("Submission document must be a JSON object")
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a CompatForge community submission")
    parser.add_argument("submission", type=Path)
    args = parser.parse_args()

    document = _load_submission(args.submission)
    result = {
        "payload_sha256": payload_sha256(document),
        "submission_fingerprint": submission_fingerprint(document),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
