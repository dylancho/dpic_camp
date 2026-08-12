import json

import pytest
from pydantic import ValidationError

from agents.proven_scalability.schema import (
    UNCALIBRATED,
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
            archetype="materials",
            thresholds={"A3": "pilot run >= 2"},
            thresholds_injected=True,
        ),
        evidence=[],
        diligence_questions=[],
    )
    restored = ProvenScalabilityResult.model_validate_json(result.model_dump_json())
    assert restored == result


def test_calibration_archetype_injected_is_derived_and_serialized():
    """PM 오케스트레이터가 JSON으로 받아야 하므로 계산 필드도 직렬화돼야 한다."""
    assert Calibration(archetype="materials").archetype_injected is True
    assert Calibration(archetype=UNCALIBRATED).archetype_injected is False
    dumped = json.loads(Calibration(archetype=UNCALIBRATED).model_dump_json())
    assert dumped["archetype_injected"] is False
    assert dumped["thresholds_injected"] is False


def test_resolved_statuses_defaults_to_empty_when_not_supplied():
    """직접 생성 시(스코어러를 거치지 않을 때) resolved_statuses는 순수 추가 필드다."""
    result = ProvenScalabilityResult(
        verdict="PASS",
        score=25,
        block_scores=BlockScores(a=12, b=8, c=5),
        gate_failed=[],
        evidence_coverage=1.0,
        calibration=Calibration(archetype="materials"),
        evidence=[],
        diligence_questions=[],
    )
    assert result.resolved_statuses == {}
