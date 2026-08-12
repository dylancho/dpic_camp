import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import agents.proven_scalability.schema as schema_module
from agents.proven_scalability.schema import (
    CRITERION_IDS,
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


def test_evidence_rejects_unknown_criterion_id():
    """추출 모델이 'A1'이나 'A1_poc'로 흘리면 여기서 걸려야 한다.

    조용히 버리면 결과가 커버리지 0.0의 INSUFFICIENT_EVIDENCE로 나오는데, 이는
    '공개 근거가 정말 없는 기업'과 구분이 불가능하다. 그 구분이 이 설계의 핵심이다.
    """
    for bad_id in ("A1", "A1_poc", "a1_poc_reproducibility", "Z9_unknown"):
        with pytest.raises(ValidationError):
            Evidence(
                criterion_id=bad_id,
                status="MET",
                source_tier=1,
                quote="...",
            )


def test_criterion_id_enum_reaches_the_json_schema_sent_to_the_api():
    """messages.parse가 보내는 JSON 스키마에 enum이 실려야 API가 생성 자체를 제약한다."""
    from agents.proven_scalability.criteria import criterion_ids

    schema = Evidence.model_json_schema()
    field = schema["properties"]["criterion_id"]
    enum = field.get("enum") or schema["$defs"][field["$ref"].split("/")[-1]]["enum"]
    assert set(enum) == criterion_ids()
    assert set(enum) == set(CRITERION_IDS)


def test_evidence_json_schema_does_not_teach_the_model_to_inflate_tiers():
    """Field(description=...)는 API로 나가는 JSON 스키마에 실린다.

    "tier 3 하나만으로 MET을 매기면 강등된다"는 감사용 설명이 거기 실리면, 모델에게
    등급을 부풀릴 동기와 방법을 함께 알려주는 꼴이다. 프롬프트는 정반대를 지시한다.
    클래스 docstring도 마찬가지로 직렬화되므로 설명은 모듈 주석으로 옮겼다.
    """
    serialized = json.dumps(Evidence.model_json_schema(), ensure_ascii=False)
    for lever in ("강등", "UNVERIFIABLE로", "resolved_statuses", "scoring.score"):
        assert lever not in serialized, f"스키마에 {lever!r}가 실려 모델에게 전달된다"
    # 설명 자체는 소스에 남아 있어야 한다 — 감사자를 위한 것이므로 삭제가 아니라 이동이다
    source = Path(schema_module.__file__).read_text(encoding="utf-8")
    assert "강등" in source


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
