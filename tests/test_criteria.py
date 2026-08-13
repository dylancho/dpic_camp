from agents.proven_scalability.criteria import (
    CRITERIA,
    criteria_for,
    criterion_ids,
    resolve_thresholds,
)
from agents.proven_scalability.schema import UNCALIBRATED


def test_block_composition():
    assert len(criteria_for("A")) == 3
    assert len(criteria_for("B")) == 4
    assert len(criteria_for("C")) == 3
    assert len(CRITERIA) == 10


def test_criterion_ids_are_unique():
    assert len(criterion_ids()) == len(CRITERIA)


def test_software_archetype_replaces_hardware_thresholds():
    cal = resolve_thresholds("software_ai_robotics", None)
    assert cal.archetype == "software_ai_robotics"
    # 하드웨어의 1,000시간 기준을 그대로 적용하지 않는다
    assert "1,000" not in cal.thresholds["A3_field_operation_hours"]
    # C 블록도 SW 문구로 치환된다
    assert cal.thresholds["C1_capacity_plan"] != _default("C1_capacity_plan")


def test_deep_tech_archetype_does_not_use_hardware_hours():
    cal = resolve_thresholds("deep_tech", None)
    assert "1,000" not in cal.thresholds["A3_field_operation_hours"]


def test_injected_thresholds_win_over_archetype_defaults():
    cal = resolve_thresholds(
        "materials", {"A1_poc_reproducibility": "고객 qualification 3건 이상"}
    )
    assert cal.thresholds["A1_poc_reproducibility"] == "고객 qualification 3건 이상"
    assert cal.thresholds_injected is True


def test_missing_calibration_is_flagged_not_guessed():
    cal = resolve_thresholds(None, None)
    assert cal.archetype_injected is False
    assert cal.archetype == UNCALIBRATED == "uncalibrated"
    assert cal.note is not None
    # 중립 기준은 원칙 원문 그대로
    assert cal.thresholds["A3_field_operation_hours"] == _default(
        "A3_field_operation_hours"
    )


def test_archetype_without_threshold_overrides_is_still_calibrated():
    """아키타입은 왔는데 항목별 오버라이드가 없는 경우 — 두 개념을 섞으면 안 된다.

    CLI에는 --thresholds 플래그가 없으므로 `--archetype materials` 실행은 전부
    이 경로를 탄다. 여기서 uncalibrated로 잘못 표시하면 매 실행이 거짓 경고를 단다.
    """
    cal = resolve_thresholds("materials", None)
    assert cal.archetype_injected is True, "아키타입은 주입됐다"
    assert cal.thresholds_injected is False, "항목별 오버라이드는 없었다"
    # 그리고 실제로 materials 오버라이드가 적용돼 있어야 한다
    assert cal.thresholds["A1_poc_reproducibility"] != _default(
        "A1_poc_reproducibility"
    )
    assert cal.note is None


def test_unknown_archetype_keeps_name_but_notes_neutral_fallback():
    """알 수 없는 아키타입은 uncalibrated로 강등하지 않는다 — PM이 준 이름은 보존하고
    중립 기준을 썼다는 사실만 note로 남긴다."""
    cal = resolve_thresholds("wetware_biotech", None)
    assert cal.archetype == "wetware_biotech"
    assert cal.archetype_injected is True
    assert cal.note is not None
    assert "wetware_biotech" in cal.note
    # 오버라이드 테이블에 없으므로 전 항목이 원칙 원문 그대로다
    for criterion in CRITERIA:
        assert cal.thresholds[criterion.id] == criterion.default_threshold


def _default(criterion_id: str) -> str:
    return next(c.default_threshold for c in CRITERIA if c.id == criterion_id)
