import agents.proven_scalability.scoring as scoring_module
from agents.proven_scalability.criteria import CRITERIA, resolve_thresholds
from agents.proven_scalability.schema import BlockScores, Evidence
from agents.proven_scalability.scoring import (
    build_diligence_questions,
    decide_verdict,
    evidence_coverage,
    gate_failures,
    met_tier_profile,
    resolve_statuses,
    score,
    score_block,
)
from tests.fixtures.evidence import ev

CAL = resolve_thresholds("industrial_hardware", None)


# --- 등급 필터 ---


def test_tier_3_only_met_is_accepted():
    # 2026-08-13 정책 변경: 3급(언론 보도) 단독 근거도 이제 MET을 뒷받침한다 —
    # 비상장 기업의 공개 근거가 거의 전부 3~4급이라 예전 필터를 쓰면 모든 항목이
    # 강등돼 서로 다른 기업이 구분 불가능한 0점으로 나왔다. 오너의 명시적 결정.
    statuses = resolve_statuses([ev("A1_poc_reproducibility", "MET", tier=3)])
    assert statuses["A1_poc_reproducibility"] == "MET"


def test_tier_4_only_met_is_accepted():
    # 4급(회사 자체 발표·IR·홈페이지) 단독 근거도 이제 MET을 뒷받침한다. 같은 정책 변경.
    statuses = resolve_statuses([ev("A2_third_party_validation", "MET", tier=4)])
    assert statuses["A2_third_party_validation"] == "MET"


def test_credible_tiers_mechanism_still_demotes_when_narrowed(monkeypatch):
    """강등 메커니즘(apply_tier_filter) 자체는 살아 있다 — _CREDIBLE_TIERS를

    좁히면 정책을 즉시 원복할 수 있어야 한다. 이 테스트가 그 배선을 고정한다:
    정책이 다시 {1, 2}로 좁혀지면 3급 단독 MET은 여전히 강등돼야 한다.
    """
    monkeypatch.setattr(scoring_module, "_CREDIBLE_TIERS", frozenset({1, 2}))
    statuses = scoring_module.resolve_statuses(
        [ev("A1_poc_reproducibility", "MET", tier=3)]
    )
    assert statuses["A1_poc_reproducibility"] == "UNVERIFIABLE"


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


def test_tier_2_met_is_credible_and_survives():
    # 2급(제3자 공인 시험성적서·peer-reviewed 논문)은 A2 "제3자 검증"이
    # 근본적으로 의존하는 등급이다 — 1급으로만 좁혀지면 안 된다
    statuses = resolve_statuses([ev("A2_third_party_validation", "MET", tier=2)])
    assert statuses["A2_third_party_validation"] == "MET"


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


def _rogue_evidence(criterion_id: str) -> Evidence:
    """스키마 검증을 우회해 만든 잘못된 ID의 Evidence.

    criterion_id가 Literal이 된 뒤로 정상 경로(추출 모델의 출력 포함)에서는 이런
    값이 만들어질 수 없다. 그래도 스코어러의 방어는 2선으로 남겨 두고, 그 방어가
    '조용히'가 아니라 '기록을 남기고' 동작하는지 확인한다.
    """
    return Evidence.model_construct(
        criterion_id=criterion_id, status="MET", source_tier=1, quote="인용"
    )


def test_unknown_criterion_id_is_dropped_not_crashed():
    # 리서처가 존재하지 않는 항목 ID를 헛짚어도 스코어러는 죽지 않는다
    statuses = resolve_statuses([_rogue_evidence("Z9_not_a_real_criterion")])
    assert len(statuses) == 10
    assert set(statuses.values()) == {"UNVERIFIABLE"}


def test_dropped_criterion_ids_are_recorded_in_research_notes():
    """버려진 ID를 기록하지 않으면 커버리지 0.0이 '근거 없는 기업'과 구분되지 않는다."""
    result = score(
        [_rogue_evidence("A1"), _rogue_evidence("A1_poc")],
        resolve_thresholds("materials", None),
    )
    assert result.evidence_coverage == 0.0
    joined = " ".join(result.research_notes)
    assert "A1_poc" in joined and "A1" in joined
    assert "2" in joined  # 버려진 건수


def test_research_notes_are_empty_when_nothing_went_wrong():
    result = score([ev("A1_poc_reproducibility")], resolve_thresholds("materials", None))
    assert result.research_notes == []


def test_upstream_research_notes_are_carried_through():
    result = score(
        [ev("A1_poc_reproducibility")],
        resolve_thresholds("materials", None),
        research_notes=["(A) 블록: max_iterations 소진으로 조사가 중단됐다"],
    )
    assert result.research_notes == ["(A) 블록: max_iterations 소진으로 조사가 중단됐다"]


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
    # A·B게이트는 각각 최소 충족 개수만 넘으면 통과다. B3/B4가 조사되지 않아
    # UNVERIFIABLE로 남든, 조사됐지만 NOT_MET이든 — 게이트 자체를 넘겼다면
    # 남은 두 항목의 상태와 무관하게 PASS여야 한다
    statuses_unverifiable = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
            # B3_domain_expertise, B4_lab_publication_track: 미조사 → UNVERIFIABLE
        ]
    )
    assert statuses_unverifiable["B3_domain_expertise"] == "UNVERIFIABLE"
    assert statuses_unverifiable["B4_lab_publication_track"] == "UNVERIFIABLE"
    assert decide_verdict(statuses_unverifiable) == "PASS"

    statuses_not_met = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
            ev("B3_domain_expertise", "NOT_MET"),
            ev("B4_lab_publication_track", "NOT_MET"),
        ]
    )
    assert decide_verdict(statuses_not_met) == "PASS"


# --- 커버리지 ---


def test_coverage_counts_non_unverifiable_ratio():
    statuses = resolve_statuses(
        [ev("A1_poc_reproducibility"), ev("B1_exchange_tech_grade", "NOT_MET")]
    )
    assert evidence_coverage(statuses) == 0.2  # 10개 중 2개


def test_coverage_is_zero_with_no_evidence():
    assert evidence_coverage(resolve_statuses([])) == 0.0


# --- 실사 질문 ---


def test_diligence_questions_use_calibration_threshold_not_default():
    # software_ai_robotics는 A3의 기준을 "가동시간" 대신 "운영 기간과 uptime"으로
    # 치환한다. calibration이 무시되면 분석가에게 잘못된(적용되지 않는) 기준을
    # 실사 질문으로 내보내게 된다
    cal = resolve_thresholds("software_ai_robotics", None)
    statuses = resolve_statuses([])  # A3 포함 전부 UNVERIFIABLE
    questions = build_diligence_questions(statuses, cal)
    a3_question = next(
        q for q in questions if q.startswith("[A3_field_operation_hours]")
    )
    assert "운영 기간과 uptime" in a3_question
    assert "1,000시간" not in a3_question


def test_diligence_questions_follow_criteria_definition_order():
    # A1→C3 순서가 stable해야 한다. dict 순회나 알파벳순으로 새면 이 테스트가 잡는다
    statuses = resolve_statuses(
        [
            ev("C3_supply_chain", "NOT_MET"),  # MET/NOT_MET인 것들은 질문에 안 뜬다
        ]
    )
    # A1,A2,A3,B1,B2,B3,B4,C1,C2 모두 UNVERIFIABLE — C3만 NOT_MET
    questions = build_diligence_questions(statuses, CAL)
    expected_order = [c.id for c in CRITERIA if c.id != "C3_supply_chain"]
    actual_order = [q.split("]")[0][1:] for q in questions]
    assert actual_order == expected_order


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
    assert result.evidence_coverage == 0.4  # 10개 중 4개 조사됨


def test_score_populates_gate_failed_when_gates_fail():
    result = score([], CAL)  # 증거 없음 — A, B 게이트 모두 실패
    assert result.gate_failed == ["A", "B"]
    assert result.block_scores == BlockScores(a=0, b=0, c=0)
    assert result.score == 0


def test_score_resolved_statuses_has_all_criteria():
    result = score([ev("A1_poc_reproducibility")], CAL)
    assert set(result.resolved_statuses) == {c.id for c in CRITERIA}


def test_score_resolved_statuses_can_diverge_from_raw_evidence_status_under_narrowed_policy(
    monkeypatch,
):
    """evidence[i].status는 필터 이전 값이라 최종 판정과 어긋날 수 있다 — 이것이 정상이다.

    현재 정책(1~4급 전부 신뢰)에서는 tier 3 단독 MET이 그대로 살아남으므로 이 사례로는
    발산이 재현되지 않는다. 발산 자체는 apply_tier_filter가 여전히 만들어낼 수 있는
    메커니즘이므로, _CREDIBLE_TIERS를 좁혀 그 경로가 살아 있음을 확인한다. evidence
    리스트 자체는 원문 그대로(MET) 남아야 한다 — 누군가 나중에 evidence를 직접 고쳐서
    "일치"시키면 감사 추적이 무너진다.
    """
    monkeypatch.setattr(scoring_module, "_CREDIBLE_TIERS", frozenset({1, 2}))
    result = scoring_module.score([ev("A1_poc_reproducibility", "MET", tier=3)], CAL)

    assert result.evidence[0].status == "MET"
    assert result.resolved_statuses["A1_poc_reproducibility"] == "UNVERIFIABLE"


def test_score_tier_3_only_met_is_met_under_current_policy():
    """현재 정책에서는 tier 3 단독 MET이 발산 없이 그대로 살아남는다."""
    result = score([ev("A1_poc_reproducibility", "MET", tier=3)], CAL)

    assert result.evidence[0].status == "MET"
    assert result.resolved_statuses["A1_poc_reproducibility"] == "MET"


# --- 근거 등급 프로필 ---


def test_met_tier_profile_records_strongest_tier_per_met_criterion():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility", "MET", tier=3),
            ev("A1_poc_reproducibility", "MET", tier=1),
            ev("B1_exchange_tech_grade", "MET", tier=4),
        ]
    )
    profile = met_tier_profile(
        [
            ev("A1_poc_reproducibility", "MET", tier=3),
            ev("A1_poc_reproducibility", "MET", tier=1),
            ev("B1_exchange_tech_grade", "MET", tier=4),
        ],
        statuses,
    )
    assert profile == {"A1_poc_reproducibility": 1, "B1_exchange_tech_grade": 4}


def test_met_tier_profile_excludes_non_met_criteria():
    evidence = [ev("A3_field_operation_hours", "NOT_MET", tier=1)]
    statuses = resolve_statuses(evidence)
    assert met_tier_profile(evidence, statuses) == {}


def test_score_populates_met_tier_profile():
    result = score(
        [
            ev("A1_poc_reproducibility", "MET", tier=3),
            ev("B1_exchange_tech_grade", "MET", tier=1),
        ],
        CAL,
    )
    assert result.met_tier_profile == {
        "A1_poc_reproducibility": 3,
        "B1_exchange_tech_grade": 1,
    }


def test_score_adds_research_note_when_met_rests_only_on_weak_tiers():
    result = score([ev("A1_poc_reproducibility", "MET", tier=4)], CAL)
    joined = " ".join(result.research_notes)
    assert "A1_poc_reproducibility" in joined
    assert "3~4급" in joined


def test_score_does_not_add_weak_tier_note_when_met_rests_on_strong_tier():
    result = score([ev("A1_poc_reproducibility", "MET", tier=1)], CAL)
    assert not any("3~4급" in note for note in result.research_notes)
