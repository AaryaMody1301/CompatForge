"""Prepare hash-exact community evidence refresh pull requests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import ContractValidationError, validate_document

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_CANDIDATES = 200
USER_AGENT = "CompatForge-community-refresh/1.0"
OBSERVATION_ID_RE = re.compile(r"^obs_[a-z0-9][a-z0-9_-]{5,63}$")
DEVICE_ID_RE = re.compile(r"^usb:[0-9A-F]{4}:[0-9A-F]{4}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_PREFIX = (
    "https://github.com/AaryaMody1301/CompatForge/blob/main/"
    "data/evidence/observations/"
)


class CommunityRefreshError(ValueError):
    """Raised when a community refresh candidate violates the trust boundary."""


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_sha256(payload: Any) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(content)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CommunityRefreshError(f"timestamp must include a timezone: {value}")
    return parsed.astimezone(UTC)


def _read_json_response(response: Any, *, label: str) -> Any:
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise CommunityRefreshError(f"{label} response exceeded {MAX_RESPONSE_BYTES} bytes")
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommunityRefreshError(f"{label} returned invalid JSON") from exc


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    timeout_seconds: float,
    label: str,
) -> Any:
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        **headers,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return _read_json_response(response, label=label)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(2048).decode("utf-8", errors="replace")
        except OSError:
            pass
        message = f"{label} failed with HTTP {exc.code}"
        if detail:
            message += f": {detail}"
        raise CommunityRefreshError(message) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CommunityRefreshError(f"{label} request failed: {type(exc).__name__}") from exc


def fetch_refresh_batch(
    *,
    supabase_url: str,
    publishable_key: str,
    email: str,
    password: str,
    timeout_seconds: float = 20.0,
) -> list[dict[str, Any]]:
    """Authenticate a dedicated refresh identity and read the bounded refresh batch."""
    base_url = supabase_url.rstrip("/")
    if not base_url.startswith("https://"):
        raise CommunityRefreshError("Supabase URL must use HTTPS")
    if not publishable_key or not email or not password:
        raise CommunityRefreshError("refresh authentication configuration is incomplete")

    auth = _post_json(
        f"{base_url}/auth/v1/token?grant_type=password",
        {"email": email, "password": password},
        headers={"apikey": publishable_key},
        timeout_seconds=timeout_seconds,
        label="Supabase refresh authentication",
    )
    if not isinstance(auth, dict) or not isinstance(auth.get("access_token"), str):
        raise CommunityRefreshError("Supabase authentication did not return an access token")

    batch = _post_json(
        f"{base_url}/rest/v1/rpc/get_community_refresh_batch",
        {},
        headers={
            "apikey": publishable_key,
            "Authorization": f"Bearer {auth['access_token']}",
        },
        timeout_seconds=timeout_seconds,
        label="community refresh batch",
    )
    if not isinstance(batch, list):
        raise CommunityRefreshError("community refresh batch must be a JSON array")
    if len(batch) > MAX_CANDIDATES:
        raise CommunityRefreshError(
            f"community refresh batch exceeds the {MAX_CANDIDATES} candidate limit"
        )
    if not all(isinstance(item, dict) for item in batch):
        raise CommunityRefreshError("community refresh batch entries must be JSON objects")
    return batch


def _required_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise CommunityRefreshError(f"candidate {key} must be a non-empty string")
    return value


def validate_candidate(item: dict[str, Any]) -> dict[str, Any]:
    """Verify one batch row against its immutable database hash and public contract."""
    submission_id = _required_string(item, "submission_id")
    try:
        uuid.UUID(submission_id)
    except ValueError as exc:
        raise CommunityRefreshError(f"invalid submission UUID: {submission_id}") from exc

    observation_id = _required_string(item, "observation_id")
    if OBSERVATION_ID_RE.fullmatch(observation_id) is None:
        raise CommunityRefreshError(f"invalid community observation ID: {observation_id}")

    device_id = _required_string(item, "device_id")
    if DEVICE_ID_RE.fullmatch(device_id) is None:
        raise CommunityRefreshError(f"invalid device ID for {observation_id}: {device_id}")

    observation_sha256 = _required_string(item, "observation_sha256")
    if SHA256_RE.fullmatch(observation_sha256) is None:
        raise CommunityRefreshError(f"invalid observation SHA-256 for {observation_id}")

    source_payload_sha256 = _required_string(item, "source_payload_sha256")
    if SHA256_RE.fullmatch(source_payload_sha256) is None:
        raise CommunityRefreshError(f"invalid source payload SHA-256 for {observation_id}")

    created_at = _required_string(item, "created_at")
    _parse_timestamp(created_at)

    observation_text = _required_string(item, "observation_text")
    observation_bytes = observation_text.encode("utf-8")
    actual_sha256 = _sha256_bytes(observation_bytes)
    if actual_sha256 != observation_sha256:
        raise CommunityRefreshError(
            f"accepted candidate hash mismatch for {observation_id}: "
            f"expected {observation_sha256}, got {actual_sha256}"
        )

    try:
        parsed_observation = json.loads(observation_text)
    except json.JSONDecodeError as exc:
        raise CommunityRefreshError(
            f"accepted candidate text is invalid JSON for {observation_id}"
        ) from exc
    if not isinstance(parsed_observation, dict):
        raise CommunityRefreshError(f"accepted candidate must be an object: {observation_id}")

    rpc_observation = item.get("observation")
    if not isinstance(rpc_observation, dict) or parsed_observation != rpc_observation:
        raise CommunityRefreshError(
            f"accepted candidate JSON/text disagree for {observation_id}"
        )

    if parsed_observation.get("record_type") != "compatibility_observation":
        raise CommunityRefreshError(f"candidate is not a compatibility observation: {observation_id}")
    if parsed_observation.get("observation_id") != observation_id:
        raise CommunityRefreshError(f"candidate observation ID mismatch: {observation_id}")
    if parsed_observation.get("device_id") != device_id:
        raise CommunityRefreshError(f"candidate device ID mismatch: {observation_id}")

    evidence = parsed_observation.get("evidence")
    expected_source_url = f"{SOURCE_PREFIX}{observation_id}.json"
    if not isinstance(evidence, dict) or evidence.get("source_type") != "community_report":
        raise CommunityRefreshError(f"candidate is not community evidence: {observation_id}")
    if evidence.get("source_url") != expected_source_url:
        raise CommunityRefreshError(
            f"candidate repository source URL mismatch for {observation_id}"
        )

    try:
        validate_document(parsed_observation, source=f"accepted candidate {observation_id}")
    except ContractValidationError as exc:
        raise CommunityRefreshError(str(exc)) from exc

    return {
        "submission_id": submission_id,
        "observation_id": observation_id,
        "device_id": device_id,
        "observation": parsed_observation,
        "observation_text": observation_text,
        "observation_sha256": observation_sha256,
        "source_payload_sha256": source_payload_sha256,
        "created_at": created_at,
    }


def _candidate_identity(candidate: dict[str, Any]) -> dict[str, str]:
    return {
        "submission_id": candidate["submission_id"],
        "observation_id": candidate["observation_id"],
        "observation_sha256": candidate["observation_sha256"],
        "source_payload_sha256": candidate["source_payload_sha256"],
    }


def _manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    return _canonical_sha256(payload)


def prepare_batch(
    batch: list[dict[str, Any]],
    *,
    repository_root: Path,
    base_commit: str,
    prepared_at: str,
) -> dict[str, Any]:
    """Materialize new candidates byte-for-byte and write a review manifest."""
    if COMMIT_SHA_RE.fullmatch(base_commit) is None:
        raise CommunityRefreshError("base commit must be a full 40-character Git SHA")
    prepared_at_dt = _parse_timestamp(prepared_at)
    if len(batch) > MAX_CANDIDATES:
        raise CommunityRefreshError(
            f"community refresh batch exceeds the {MAX_CANDIDATES} candidate limit"
        )

    candidates = [validate_candidate(item) for item in batch]
    candidates.sort(key=lambda item: (item["created_at"], item["observation_id"]))

    submission_ids = [item["submission_id"] for item in candidates]
    observation_ids = [item["observation_id"] for item in candidates]
    if len(set(submission_ids)) != len(submission_ids):
        raise CommunityRefreshError("refresh batch contains duplicate submission IDs")
    if len(set(observation_ids)) != len(observation_ids):
        raise CommunityRefreshError("refresh batch contains duplicate observation IDs")

    added: list[dict[str, Any]] = []
    already_present = 0
    for candidate in candidates:
        relative_path = Path("data/evidence/observations") / f"{candidate['observation_id']}.json"
        target = repository_root / relative_path
        expected_bytes = candidate["observation_text"].encode("utf-8")
        if target.exists():
            existing_bytes = target.read_bytes()
            if existing_bytes != expected_bytes:
                raise CommunityRefreshError(
                    f"canonical evidence collision at {relative_path}: existing bytes do not "
                    "match the immutable accepted candidate"
                )
            already_present += 1
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(expected_bytes)
        added.append(
            {
                **_candidate_identity(candidate),
                "device_id": candidate["device_id"],
                "created_at": candidate["created_at"],
                "path": relative_path.as_posix(),
                "file_sha256": _sha256_bytes(expected_bytes),
            }
        )

    result: dict[str, Any] = {
        "prepared_at": prepared_at_dt.isoformat().replace("+00:00", "Z"),
        "base_commit": base_commit,
        "batch_count": len(candidates),
        "added": len(added),
        "already_present": already_present,
        "batch_id": None,
        "manifest_path": None,
    }
    if not added:
        return result

    batch_id = _canonical_sha256([_candidate_identity(item) for item in added])
    manifest_relative = Path("data/evidence/community-refresh") / f"{batch_id}.json"
    manifest_path = repository_root / manifest_relative
    manifest = {
        "schema_version": "1.0.0",
        "record_type": "community_refresh_manifest",
        "batch_id": batch_id,
        "base_commit": base_commit,
        "prepared_at": prepared_at_dt.isoformat().replace("+00:00", "Z"),
        "candidates": added,
        "trust_boundary": {
            "candidate_bytes_match_accepted_sha256": True,
            "automatic_publication": False,
            "publication_receipt_required_after_merge": True,
        },
    }
    manifest["manifest_sha256"] = _manifest_sha256(manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["batch_id"] = batch_id
    result["manifest_path"] = manifest_relative.as_posix()
    return result


def verify_manifest(manifest_path: Path, *, repository_root: Path) -> dict[str, Any]:
    """Verify that every committed candidate still has the exact accepted bytes."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CommunityRefreshError(f"invalid refresh manifest: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise CommunityRefreshError("refresh manifest must be a JSON object")
    if manifest.get("record_type") != "community_refresh_manifest":
        raise CommunityRefreshError("unsupported refresh manifest record type")
    if manifest.get("schema_version") != "1.0.0":
        raise CommunityRefreshError("unsupported refresh manifest schema version")
    if manifest.get("manifest_sha256") != _manifest_sha256(manifest):
        raise CommunityRefreshError("refresh manifest SHA-256 does not match its contents")

    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise CommunityRefreshError("refresh manifest must contain at least one candidate")
    if len(candidates) > MAX_CANDIDATES:
        raise CommunityRefreshError("refresh manifest exceeds the candidate limit")

    identities = []
    seen_paths: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            raise CommunityRefreshError("refresh manifest candidates must be objects")
        observation_id = _required_string(item, "observation_id")
        submission_id = _required_string(item, "submission_id")
        observation_sha256 = _required_string(item, "observation_sha256")
        source_payload_sha256 = _required_string(item, "source_payload_sha256")
        relative_path = _required_string(item, "path")
        if SHA256_RE.fullmatch(observation_sha256) is None:
            raise CommunityRefreshError(f"invalid candidate SHA-256 for {observation_id}")
        if SHA256_RE.fullmatch(source_payload_sha256) is None:
            raise CommunityRefreshError(f"invalid payload SHA-256 for {observation_id}")
        try:
            uuid.UUID(submission_id)
        except ValueError as exc:
            raise CommunityRefreshError(f"invalid submission UUID: {submission_id}") from exc

        expected_path = f"data/evidence/observations/{observation_id}.json"
        if relative_path != expected_path:
            raise CommunityRefreshError(f"unexpected candidate path for {observation_id}")
        if relative_path in seen_paths:
            raise CommunityRefreshError(f"duplicate candidate path: {relative_path}")
        seen_paths.add(relative_path)

        target = repository_root / relative_path
        if not target.is_file():
            raise CommunityRefreshError(f"candidate file is missing: {relative_path}")
        content = target.read_bytes()
        actual_sha256 = _sha256_bytes(content)
        if actual_sha256 != observation_sha256 or item.get("file_sha256") != actual_sha256:
            raise CommunityRefreshError(
                f"candidate file hash no longer matches accepted SHA-256: {observation_id}"
            )
        try:
            document = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CommunityRefreshError(f"candidate file is invalid JSON: {relative_path}") from exc
        if not isinstance(document, dict) or document.get("observation_id") != observation_id:
            raise CommunityRefreshError(f"candidate observation identity mismatch: {relative_path}")
        evidence = document.get("evidence")
        if not isinstance(evidence, dict) or evidence.get("source_type") != "community_report":
            raise CommunityRefreshError(f"candidate is not community evidence: {relative_path}")
        if evidence.get("source_url") != f"{SOURCE_PREFIX}{observation_id}.json":
            raise CommunityRefreshError(f"candidate source URL mismatch: {relative_path}")
        try:
            validate_document(document, source=relative_path)
        except ContractValidationError as exc:
            raise CommunityRefreshError(str(exc)) from exc
        identities.append(
            {
                "submission_id": submission_id,
                "observation_id": observation_id,
                "observation_sha256": observation_sha256,
                "source_payload_sha256": source_payload_sha256,
            }
        )

    expected_batch_id = _canonical_sha256(identities)
    if manifest.get("batch_id") != expected_batch_id:
        raise CommunityRefreshError("refresh manifest batch ID does not match candidate identities")

    trust_boundary = manifest.get("trust_boundary")
    if trust_boundary != {
        "candidate_bytes_match_accepted_sha256": True,
        "automatic_publication": False,
        "publication_receipt_required_after_merge": True,
    }:
        raise CommunityRefreshError("refresh manifest trust boundary is missing or altered")

    return {
        "batch_id": expected_batch_id,
        "candidate_count": len(candidates),
        "manifest_sha256": manifest["manifest_sha256"],
    }


def render_pr_body(manifest_path: Path) -> str:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = manifest["candidates"]
    lines = [
        "## Accepted community evidence refresh",
        "",
        f"Batch: `{manifest['batch_id']}`",
        f"Base commit: `{manifest['base_commit']}`",
        f"Manifest SHA-256: `{manifest['manifest_sha256']}`",
        "",
        "### Candidates",
        "",
    ]
    for item in candidates:
        lines.append(
            f"- `{item['observation_id']}` — candidate SHA-256 "
            f"`{item['observation_sha256']}`"
        )
    lines.extend(
        [
            "",
            "### Trust boundary",
            "",
            "Each observation file is written byte-for-byte from the PostgreSQL `jsonb::text` "
            "value whose SHA-256 was frozen at moderator acceptance. CI re-verifies those exact "
            "file bytes and the normal observation contract.",
            "",
            "Merging this PR does **not** publish the source submissions in Supabase. After merge, "
            "an admin must separately record the full merged commit SHA and the exact accepted "
            "candidate SHA-256 through the existing publication RPC.",
            "",
            "Do not edit candidate observation files in this automation branch. A semantic change "
            "would no longer match the immutable accepted candidate and must go through a new "
            "moderation decision instead.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_batch(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise CommunityRefreshError("batch file must contain a JSON array of objects")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="fetch/validate candidates and materialize PR files")
    prepare.add_argument("--batch", type=Path)
    prepare.add_argument("--repository-root", type=Path, default=Path("."))
    prepare.add_argument("--base-commit", required=True)
    prepare.add_argument("--prepared-at", required=True)
    prepare.add_argument("--timeout-seconds", type=float, default=20.0)
    prepare.add_argument("--result", type=Path, required=True)

    verify = commands.add_parser("verify", help="verify a committed community refresh manifest")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--repository-root", type=Path, default=Path("."))

    body = commands.add_parser("pr-body", help="render the review PR body from a manifest")
    body.add_argument("--manifest", type=Path, required=True)
    body.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "prepare":
            if args.batch:
                batch = _load_batch(args.batch)
            else:
                batch = fetch_refresh_batch(
                    supabase_url=os.environ.get("COMPATFORGE_SUPABASE_URL", ""),
                    publishable_key=os.environ.get(
                        "COMPATFORGE_SUPABASE_PUBLISHABLE_KEY", ""
                    ),
                    email=os.environ.get("COMPATFORGE_REFRESH_EMAIL", ""),
                    password=os.environ.get("COMPATFORGE_REFRESH_PASSWORD", ""),
                    timeout_seconds=args.timeout_seconds,
                )
            result = prepare_batch(
                batch,
                repository_root=args.repository_root,
                base_commit=args.base_commit,
                prepared_at=args.prepared_at,
            )
            _write_json(args.result, result)
            print(json.dumps(result, sort_keys=True))
            return 0

        if args.command == "verify":
            result = verify_manifest(args.manifest, repository_root=args.repository_root)
            print(json.dumps(result, sort_keys=True))
            return 0

        body_text = render_pr_body(args.manifest)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body_text, encoding="utf-8")
        return 0
    except (CommunityRefreshError, OSError, json.JSONDecodeError) as exc:
        print(f"community refresh failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
