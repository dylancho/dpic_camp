from agents.proven_scalability.criteria import (
    CRITERIA,
    criteria_for,
    criterion_ids,
    resolve_thresholds,
)


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
    assert cal.injected is True


def test_missing_calibration_is_flagged_not_guessed():
    cal = resolve_thresholds(None, None)
    assert cal.injected is False
    assert cal.archetype == "uncalibrated"
    assert cal.note is not None
    # 중립 기준은 원칙 원문 그대로
    assert cal.thresholds["A3_field_operation_hours"] == _default(
        "A3_field_operation_hours"
    )


def _default(criterion_id: str) -> str:
    return next(c.default_threshold for c in CRITERIA if c.id == criterion_id)
