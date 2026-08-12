from agents.proven_scalability.criteria import criteria_for, resolve_thresholds
from agents.proven_scalability.prompts import (
    EXTRACTION_SYSTEM,
    extraction_prompt,
    research_prompt,
)
from agents.proven_scalability.schema import Calibration


def test_research_prompt_lists_only_its_own_block():
    """블록 A의 프롬프트는 A의 기준만 포함하고 B, C의 기준은 제외한다."""
    prompt = research_prompt("A", "테스트기업", resolve_thresholds("materials", None))
    assert "A1_poc_reproducibility" in prompt
    assert "B1_exchange_tech_grade" not in prompt  # 블록 오염 방지
    assert "C1_capacity_plan" not in prompt


def test_research_prompt_cross_block_contamination_all_blocks():
    """모든 블록에 대해 자신의 기준만 포함하고 다른 블록의 기준은 제외한다."""
    for block in ("A", "B", "C"):
        prompt = research_prompt(block, "테스트기업", resolve_thresholds("materials", None))

        # 자신의 기준은 포함
        own_criteria = {c.id for c in criteria_for(block)}
        for criterion_id in own_criteria:
            assert criterion_id in prompt, f"{block} 블록 프롬프트에 {criterion_id}가 없음"

        # 다른 블록의 기준은 제외
        for other_block in ("A", "B", "C"):
            if other_block != block:
                other_criteria = {c.id for c in criteria_for(other_block)}
                for criterion_id in other_criteria:
                    assert criterion_id not in prompt, f"{block} 블록 프롬프트에 {other_block}의 {criterion_id}가 포함되어 있음"


def test_research_prompt_uses_injected_thresholds():
    cal = resolve_thresholds("software_ai_robotics", None)
    prompt = research_prompt("A", "테스트기업", cal)
    assert cal.thresholds["A3_field_operation_hours"] in prompt


def test_research_prompt_flags_uncalibrated_state():
    prompt = research_prompt("A", "테스트기업", resolve_thresholds(None, None))
    assert "중립" in prompt or "주입되지" in prompt


def test_research_prompt_hides_warning_when_injected():
    """임계치가 주입되면 uncalibrated 경고가 나타나지 않는다."""
    # 주입된 임계치로 calibration 생성
    injected_thresholds = {
        "A1_poc_reproducibility": "고객 qualification 3건 이상",
        "A2_third_party_validation": "제3자 검증 2건 이상",
        "A3_field_operation_hours": "1,500시간 이상",
    }
    cal_injected = resolve_thresholds("materials", injected_thresholds)
    assert cal_injected.thresholds_injected is True  # 주입 상태 확인

    prompt_injected = research_prompt("A", "테스트기업", cal_injected)
    assert "주입되지 않았다" not in prompt_injected  # 경고가 없어야 함

    # 비교: uncalibrated 상태는 경고가 있어야 함
    cal_uncalibrated = resolve_thresholds(None, None)
    assert cal_uncalibrated.archetype_injected is False  # uncalibrated 상태 확인

    prompt_uncalibrated = research_prompt("A", "테스트기업", cal_uncalibrated)
    assert "주입되지" in prompt_uncalibrated  # 경고가 있어야 함


def test_research_prompt_shows_archetype_thresholds_without_uncalibrated_warning():
    """아키타입만 주입되고 항목별 오버라이드가 없는 경우 — 프롬프트가 거짓말하면 안 된다.

    이 조합(`resolve_thresholds("materials", None)`)은 CLI의 모든 `--archetype`
    실행이 타는 경로다. 프롬프트에 실린 임계치는 materials 오버라이드인데
    "주입되지 않았다. 아래는 중립 기준이다"라고 붙으면 리서처에게 거짓을 말하는 것이다.
    """
    cal = resolve_thresholds("materials", None)
    prompt = research_prompt("A", "테스트기업", cal)

    # 프롬프트가 보여주는 것은 실제로 materials 오버라이드다
    assert cal.thresholds["A1_poc_reproducibility"] in prompt
    assert cal.thresholds["A3_field_operation_hours"] in prompt
    # 그러므로 "중립 기준" 경고가 붙으면 안 된다
    assert "주입되지" not in prompt
    assert "중립 기준" not in prompt
    assert "materials" in prompt


def test_research_prompt_warns_when_archetype_is_unknown():
    """오타나 미지원 아키타입은 이름만 반영되고 임계치는 중립이다 — 그 사실을 말해야 한다.

    C1 수정이 materials 경로의 거짓말을 없애면서 이 경로에 거울상 거짓말을 만들 수 있다:
    "적용 아키타입: wetware_biotech"라고 적고 경고를 떼면, 리서처는 산업별 기준이
    적용된 줄 안다. 실제로는 원칙 원문 그대로다. criteria가 만든 note가 정확히 그
    사실을 말하고 있으므로, 프롬프트와 CLI가 갈라지지 않게 그 note를 그대로 싣는다.
    """
    cal = resolve_thresholds("wetware_biotech", None)
    prompt = research_prompt("A", "테스트기업", cal)

    assert cal.note is not None
    assert cal.note in prompt, "criteria가 만든 note가 프롬프트에 도달해야 한다"
    assert "wetware_biotech" in prompt
    # 임계치는 실제로 중립이다
    for criterion in criteria_for("A"):
        assert criterion.default_threshold in prompt


def test_research_prompt_stays_quiet_for_a_known_archetype():
    """알려진 아키타입은 note가 없으므로 경고 문구가 하나도 붙지 않는다."""
    prompt = research_prompt("A", "테스트기업", resolve_thresholds("materials", None))
    assert "주의" not in prompt


def test_research_prompt_survives_calibration_with_empty_thresholds():
    """PM 주입 포맷이 미확정이라 thresholds가 비어 올 수 있다 (schema 기본값이 {}).

    scoring.py는 이미 .get(id, default_threshold)로 방어한다. 프롬프트만 KeyError로
    죽으면 계약이 반쪽이다.
    """
    cal = Calibration(archetype="materials", thresholds={})
    prompt = research_prompt("A", "테스트기업", cal)
    for criterion in criteria_for("A"):
        assert criterion.default_threshold in prompt


def test_research_prompt_forbids_judging():
    prompt = research_prompt("B", "테스트기업", resolve_thresholds("deep_tech", None))
    assert "점수" in prompt
    assert "세지 마" in prompt or "판정하지" in prompt


def test_extraction_system_defines_tier_scale():
    for tier in ("1급", "2급", "3급", "4급"):
        assert tier in EXTRACTION_SYSTEM


def test_extraction_system_does_not_disclose_the_demotion_mechanism():
    """I4에서 JSON 스키마에서 뺀 지렛대가 프롬프트 산문에 남아 있으면 똑같은 문제다.

    "3~4급 단독 근거는 자동 강등된다"를 알려주는 순간, 모델은 등급을 올려 적으면
    강등을 피할 수 있다는 것도 함께 알게 된다. 부탁으로 막을 일이 아니라 말하지 않을 일이다.
    """
    for lever in ("강등", "하위 계층", "자동으로", "scoring"):
        assert lever not in EXTRACTION_SYSTEM, f"{lever!r}가 강등 메커니즘을 노출한다"
    # 등급 자체를 정확히 매기라는 지시는 남아 있어야 한다
    assert "출처" in EXTRACTION_SYSTEM


def test_extraction_prompt_embeds_transcript():
    prompt = extraction_prompt("C", "여기가 조사 전문이다")
    assert "여기가 조사 전문이다" in prompt
    assert "C1_capacity_plan" in prompt
