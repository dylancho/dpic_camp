from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.prompts import (
    EXTRACTION_SYSTEM,
    extraction_prompt,
    research_prompt,
)


def test_research_prompt_lists_only_its_own_block():
    prompt = research_prompt("A", "테스트기업", resolve_thresholds("materials", None))
    assert "A1_poc_reproducibility" in prompt
    assert "B1_exchange_tech_grade" not in prompt  # 블록 오염 방지
    assert "C1_capacity_plan" not in prompt


def test_research_prompt_uses_injected_thresholds():
    cal = resolve_thresholds("software_ai_robotics", None)
    prompt = research_prompt("A", "테스트기업", cal)
    assert cal.thresholds["A3_field_operation_hours"] in prompt


def test_research_prompt_flags_uncalibrated_state():
    prompt = research_prompt("A", "테스트기업", resolve_thresholds(None, None))
    assert "중립" in prompt or "주입되지" in prompt


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
