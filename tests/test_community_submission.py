from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from compatforge_pipeline.contracts import ContractValidationError, validate_document
from compatforge_pipeline.submission import payload_sha256, submission_fingerprint

FIXTURE = Path("data/fixtures/community_submission.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_community_submission_fixture_is_valid() -> None:
    validate_document(_load_fixture(), source=str(FIXTURE))


def test_fingerprint_ignores_transport_metadata() -> None:
    original = _load_fixture()
    duplicate = copy.deepcopy(original)
    duplicate["client_submission_id"] = "99999999-8888-4777-8666-555555555555"
    duplicate["prepared_at"] = "2026-09-08T00:00:00Z"

    assert submission_fingerprint(original) == submission_fingerprint(duplicate)
    assert payload_sha256(original) != payload_sha256(duplicate)


def test_fingerprint_changes_when_reproduction_changes() -> None:
    original = _load_fixture()
    changed = copy.deepcopy(original)
    changed["reproduction"]["outcome"] = "fails"

    assert submission_fingerprint(original) != submission_fingerprint(changed)


def test_unknown_is_not_a_community_observation_outcome() -> None:
    document = _load_fixture()
    document["reproduction"]["outcome"] = "unknown"

    with pytest.raises(ContractValidationError):
        validate_document(document)


def test_conditional_outcome_requires_a_condition() -> None:
    document = _load_fixture()
    document["reproduction"]["outcome"] = "works_with_conditions"
    document["reproduction"]["conditions"] = []

    with pytest.raises(ContractValidationError):
        validate_document(document)
