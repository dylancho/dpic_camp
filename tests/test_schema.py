import pytest
from pydantic import ValidationError

from agents.proven_scalability.schema import (
    BlockScores,
    Calibration,
    Evidence,
    ProvenScalabilityResult,
)


def test_evidence_requires_valid_tier():
    with pytest.raises(ValidationError):
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MET",
            source_tier=5,  # 1~4만 허용
            source_url="https://example.com",
            quote="...",
        )


def test_evidence_rejects_unknown_status():
    with pytest.raises(ValidationError):
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MAYBE",
            source_tier=1,
            source_url=None,
            quote="...",
        )


def test_block_scores_total():
    assert BlockScores(a=12, b=8, c=5).total == 25
    assert BlockScores(a=0, b=0, c=0).total == 0


def test_result_round_trips_through_json():
    result = ProvenScalabilityResult(
        verdict="PASS",
        score=25,
        block_scores=BlockScores(a=12, b=8, c=5),
        gate_failed=[],
        evidence_coverage=1.0,
        calibration=Calibration(
            archetype="materials", thresholds={"A3": "pilot run >= 2"}, injected=True
        ),
        evidence=[],
        diligence_questions=[],
    )
    restored = ProvenScalabilityResult.model_validate_json(result.model_dump_json())
    assert restored == result
