from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.schema import BlockScores
from agents.proven_scalability.scoring import (
    decide_verdict,
    evidence_coverage,
    gate_failures,
    resolve_statuses,
    score,
    score_block,
)
from tests.fixtures.evidence import ev

CAL = resolve_thresholds("industrial_hardware", None)


# --- 등급 필터 ---


def test_tier_3_only_met_is_demoted_to_unverifiable():
    statuses = resolve_statuses([ev("A1_poc_reproducibility", "MET", tier=3)])
    assert statuses["A1_poc_reproducibility"] == "UNVERIFIABLE"


def test_tier_4_only_met_is_demoted():
    statuses = resolve_statuses([ev("A2_third_party_validation", "MET", tier=4)])
    assert statuses["A2_third_party_validation"] == "UNVERIFIABLE"


def test_tier_1_met_survives_alongside_tier_3():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility", "MET", tier=3),
            ev("A1_poc_reproducibility", "MET", tier=1),
        ]
    )
    assert statuses["A1_poc_reproducibility"] == "MET"


def test_tier_3_not_met_is_not_demoted():
    # 강등은 MET에만 적용된다. 미달 판정은 등급과 무관하게 유지
    statuses = resolve_statuses([ev("A3_field_operation_hours", "NOT_MET", tier=3)])
    assert statuses["A3_field_operation_hours"] == "NOT_MET"


# --- 상태 합성 ---


def test_met_beats_not_met_for_same_criterion():
    statuses = resolve_statuses(
        [
            ev("B2_registered_patents", "NOT_MET", tier=1),
            ev("B2_registered_patents", "MET", tier=1),
        ]
    )
    assert statuses["B2_registered_patents"] == "MET"


def test_unscanned_criterion_defaults_to_unverifiable():
    statuses = resolve_statuses([])
    assert len(statuses) == 10
    assert set(statuses.values()) == {"UNVERIFIABLE"}


# --- 배점 ---


def test_block_a_scores_by_count():
    ids = [
        "A1_poc_reproducibility",
        "A2_third_party_validation",
        "A3_field_operation_hours",
    ]
    for n, expected in [(1, 8), (2, 10), (3, 12)]:
        statuses = resolve_statuses([ev(i) for i in ids[:n]])
        assert score_block("A", statuses) == expected


def test_block_a_zero_when_gate_fails():
    assert score_block("A", resolve_statuses([])) == 0


def test_block_b_scores_by_count():
    ids = [
        "B1_exchange_tech_grade",
        "B2_registered_patents",
        "B3_domain_expertise",
        "B4_lab_publication_track",
    ]
    for n, expected in [(2, 5), (3, 7), (4, 8)]:
        statuses = resolve_statuses([ev(i) for i in ids[:n]])
        assert score_block("B", statuses) == expected


def test_block_b_zero_with_only_one_met():
    statuses = resolve_statuses([ev("B1_exchange_tech_grade")])
    assert score_block("B", statuses) == 0


def test_block_c_scores_by_count_without_gate():
    ids = ["C1_capacity_plan", "C2_capex_funding", "C3_supply_chain"]
    for n, expected in [(0, 0), (1, 2), (2, 4), (3, 5)]:
        statuses = resolve_statuses([ev(i) for i in ids[:n]])
        assert score_block("C", statuses) == expected


# --- 게이트와 verdict ---


def test_gate_failures_lists_both_blocks():
    assert gate_failures(resolve_statuses([])) == ["A", "B"]


def test_no_gate_failure_when_thresholds_met():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
        ]
    )
    assert gate_failures(statuses) == []


def test_verdict_pass_when_both_gates_clear():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
        ]
    )
    assert decide_verdict(statuses) == "PASS"


def test_verdict_fail_when_every_criterion_investigated_and_short():
    # 모든 항목을 조사했고 전부 기준 미달 — 조사가 끝났다는 뜻
    all_ids = list(resolve_statuses([]).keys())
    statuses = resolve_statuses([ev(i, "NOT_MET") for i in all_ids])
    assert decide_verdict(statuses) == "FAIL"


def test_verdict_insufficient_when_unverifiable_remains_in_failed_gate():
    all_ids = list(resolve_statuses([]).keys())
    evidence = [ev(i, "NOT_MET") for i in all_ids if i != "A2_third_party_validation"]
    statuses = resolve_statuses(evidence)  # A2만 UNVERIFIABLE로 남는다
    assert statuses["A2_third_party_validation"] == "UNVERIFIABLE"
    assert decide_verdict(statuses) == "INSUFFICIENT_EVIDENCE"


def test_unverifiable_in_passing_gate_does_not_block_pass():
    # A게이트는 통과. B의 UNVERIFIABLE은 verdict를 바꾸지 않는다
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
        ]
    )
    assert decide_verdict(statuses) == "PASS"


# --- 커버리지 ---


def test_coverage_counts_non_unverifiable_ratio():
    statuses = resolve_statuses(
        [ev("A1_poc_reproducibility"), ev("B1_exchange_tech_grade", "NOT_MET")]
    )
    assert evidence_coverage(statuses) == 0.2  # 10개 중 2개


def test_coverage_is_zero_with_no_evidence():
    assert evidence_coverage(resolve_statuses([])) == 0.0


# --- 결정론 ---


def test_same_evidence_always_yields_same_result():
    evidence = [
        ev("A1_poc_reproducibility"),
        ev("A2_third_party_validation", "NOT_MET"),
        ev("B1_exchange_tech_grade"),
        ev("B2_registered_patents", tier=2),
        ev("C1_capacity_plan"),
    ]
    first = score(evidence, CAL)
    second = score(list(reversed(evidence)), CAL)
    assert first.score == second.score
    assert first.verdict == second.verdict
    assert first.block_scores == second.block_scores


def test_score_assembles_full_result():
    result = score(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
            ev("C1_capacity_plan"),
        ],
        CAL,
    )
    assert result.verdict == "PASS"
    assert result.block_scores == BlockScores(a=8, b=5, c=2)
    assert result.score == 15
    assert result.gate_failed == []
    assert result.diligence_questions  # UNVERIFIABLE 항목이 남아 있으므로 비어 있지 않다
