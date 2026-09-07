import json
from pathlib import Path

import pytest
from compatforge_pipeline.contracts import ContractValidationError, validate_document
from compatforge_pipeline.validate import validate_paths

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_all_public_phase_1_fixtures_validate() -> None:
    assert validate_paths([ROOT / "data" / "fixtures"]) == 2


def test_unknown_observation_outcome_is_rejected() -> None:
    document = load(ROOT / "tests" / "fixtures" / "observation.invalid.json")
    with pytest.raises(ContractValidationError, match="probably_works"):
        validate_document(document)


def test_conditional_outcome_requires_conditions() -> None:
    document = load(ROOT / "data" / "fixtures" / "observation.synthetic.json")
    document.pop("conditions")
    with pytest.raises(ContractValidationError, match="conditions"):
        validate_document(document)


def test_observation_rejects_non_https_evidence_url() -> None:
    document = load(ROOT / "data" / "fixtures" / "observation.synthetic.json")
    document["evidence"]["source_url"] = "http://example.com/evidence"
    with pytest.raises(ContractValidationError, match="source_url"):
        validate_document(document)
