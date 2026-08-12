from agents.proven_scalability.criteria import criteria_for, resolve_thresholds
from agents.proven_scalability.prompts import (
    EXTRACTION_SYSTEM,
    extraction_prompt,
    research_prompt,
)


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
    assert cal_injected.injected is True  # 주입 상태 확인

    prompt_injected = research_prompt("A", "테스트기업", cal_injected)
    assert "주입되지 않았다" not in prompt_injected  # 경고가 없어야 함

    # 비교: uncalibrated 상태는 경고가 있어야 함
    cal_uncalibrated = resolve_thresholds(None, None)
    assert cal_uncalibrated.injected is False  # uncalibrated 상태 확인

    prompt_uncalibrated = research_prompt("A", "테스트기업", cal_uncalibrated)
    assert "주입되지" in prompt_uncalibrated  # 경고가 있어야 함


def test_research_prompt_forbids_judging():
    prompt = research_prompt("B", "테스트기업", resolve_thresholds("deep_tech", None))
    assert "점수" in prompt
    assert "세지 마" in prompt or "판정하지" in prompt


def test_extraction_system_defines_tier_scale():
    for tier in ("1급", "2급", "3급", "4급"):
        assert tier in EXTRACTION_SYSTEM


def test_extraction_prompt_embeds_transcript():
    prompt = extraction_prompt("C", "여기가 조사 전문이다")
    assert "여기가 조사 전문이다" in prompt
    assert "C1_capacity_plan" in prompt
