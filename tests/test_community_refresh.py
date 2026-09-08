import hashlib
import json
from pathlib import Path

import pytest
from compatforge_pipeline import community_refresh

BASE_COMMIT = "a" * 40
PREPARED_AT = "2026-09-08T08:00:00Z"
SUBMISSION_ID = "11111111-1111-1111-1111-111111111111"
OBSERVATION_ID = "obs_community_11111111111111111111111111111111"
SOURCE_PAYLOAD_SHA256 = "b" * 64


def _observation() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "record_type": "compatibility_observation",
        "observation_id": OBSERVATION_ID,
        "device_id": "usb:0403:6001",
        "host": {
            "manufacturer": "Acer",
            "model": "Aspire 14 AI",
            "architecture": "arm64",
            "operating_system": {
                "family": "windows",
                "version": "11",
                "build": "25H2",
            },
        },
        "connection_path": [{"kind": "direct_port"}],
        "driver": {"name": "FTDI D2XX", "version": "1.2.3"},
        "firmware_version": "1.0",
        "outcome": "works_with_conditions",
        "conditions": ["The tested workflow used the stated driver version."],
        "evidence": {
            "source_type": "community_report",
            "source_url": (
                "https://github.com/AaryaMody1301/CompatForge/blob/main/"
                f"data/evidence/observations/{OBSERVATION_ID}.json"
            ),
            "source_title": f"CompatForge reviewed community reproduction {OBSERVATION_ID}",
            "source_excerpt": "Connected the reviewed FT232R target directly.",
        },
        "observed_at": "2026-09-01T10:00:00.000Z",
        "recorded_at": "2026-09-08T05:00:00.000Z",
        "limitations": ["This is a single-host community reproduction."],
        "notes": (
            "Reviewed community reproduction. Source payload SHA-256: "
            f"{SOURCE_PAYLOAD_SHA256}."
        ),
    }


def _batch_item() -> dict[str, object]:
    observation = _observation()
    observation_text = json.dumps(observation, sort_keys=True, separators=(",", ":"))
    observation_sha256 = hashlib.sha256(observation_text.encode()).hexdigest()
    return {
        "submission_id": SUBMISSION_ID,
        "observation_id": OBSERVATION_ID,
        "device_id": "usb:0403:6001",
        "observation": observation,
        "observation_text": observation_text,
        "observation_sha256": observation_sha256,
        "source_payload_sha256": SOURCE_PAYLOAD_SHA256,
        "created_at": "2026-09-08T07:45:00Z",
    }


def test_prepare_batch_writes_exact_candidate_bytes_and_manifest(tmp_path: Path) -> None:
    item = _batch_item()
    result = community_refresh.prepare_batch(
        [item],
        repository_root=tmp_path,
        base_commit=BASE_COMMIT,
        prepared_at=PREPARED_AT,
    )

    assert result["added"] == 1
    assert result["already_present"] == 0
    assert result["batch_id"]
    assert result["manifest_path"]

    observation_path = tmp_path / "data/evidence/observations" / f"{OBSERVATION_ID}.json"
    assert observation_path.read_text(encoding="utf-8") == item["observation_text"]
    assert hashlib.sha256(observation_path.read_bytes()).hexdigest() == item["observation_sha256"]

    manifest_path = tmp_path / str(result["manifest_path"])
    verified = community_refresh.verify_manifest(manifest_path, repository_root=tmp_path)
    assert verified["batch_id"] == result["batch_id"]
    assert verified["candidate_count"] == 1


def test_prepare_batch_rejects_candidate_hash_mismatch(tmp_path: Path) -> None:
    item = _batch_item()
    item["observation_sha256"] = "0" * 64

    with pytest.raises(community_refresh.CommunityRefreshError, match="hash mismatch"):
        community_refresh.prepare_batch(
            [item],
            repository_root=tmp_path,
            base_commit=BASE_COMMIT,
            prepared_at=PREPARED_AT,
        )


def test_prepare_batch_rejects_existing_file_collision(tmp_path: Path) -> None:
    item = _batch_item()
    observation_path = tmp_path / "data/evidence/observations" / f"{OBSERVATION_ID}.json"
    observation_path.parent.mkdir(parents=True)
    observation_path.write_text(json.dumps(_observation(), indent=2), encoding="utf-8")

    with pytest.raises(community_refresh.CommunityRefreshError, match="collision"):
        community_refresh.prepare_batch(
            [item],
            repository_root=tmp_path,
            base_commit=BASE_COMMIT,
            prepared_at=PREPARED_AT,
        )


def test_prepare_batch_is_noop_when_exact_candidate_is_already_present(tmp_path: Path) -> None:
    item = _batch_item()
    observation_path = tmp_path / "data/evidence/observations" / f"{OBSERVATION_ID}.json"
    observation_path.parent.mkdir(parents=True)
    observation_path.write_text(str(item["observation_text"]), encoding="utf-8")

    result = community_refresh.prepare_batch(
        [item],
        repository_root=tmp_path,
        base_commit=BASE_COMMIT,
        prepared_at=PREPARED_AT,
    )

    assert result["added"] == 0
    assert result["already_present"] == 1
    assert result["batch_id"] is None
    assert result["manifest_path"] is None
    assert not (tmp_path / "data/evidence/community-refresh").exists()


def test_verify_manifest_detects_post_prepare_candidate_edit(tmp_path: Path) -> None:
    item = _batch_item()
    result = community_refresh.prepare_batch(
        [item],
        repository_root=tmp_path,
        base_commit=BASE_COMMIT,
        prepared_at=PREPARED_AT,
    )
    observation_path = tmp_path / "data/evidence/observations" / f"{OBSERVATION_ID}.json"
    observation_path.write_text(json.dumps(_observation(), indent=2), encoding="utf-8")

    with pytest.raises(community_refresh.CommunityRefreshError, match="hash no longer matches"):
        community_refresh.verify_manifest(
            tmp_path / str(result["manifest_path"]),
            repository_root=tmp_path,
        )


def test_pr_body_keeps_merge_separate_from_publication(tmp_path: Path) -> None:
    result = community_refresh.prepare_batch(
        [_batch_item()],
        repository_root=tmp_path,
        base_commit=BASE_COMMIT,
        prepared_at=PREPARED_AT,
    )
    body = community_refresh.render_pr_body(tmp_path / str(result["manifest_path"]))

    assert OBSERVATION_ID in body
    assert "does **not** publish" in body
    assert "full merged commit SHA" in body
