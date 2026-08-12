"""등급 필터·게이트·배점·verdict.

이 모듈에는 LLM 호출이 없다. 같은 Evidence 집합이면 항상 같은 결과가 나온다.
"""

from __future__ import annotations

from agents.proven_scalability.criteria import CRITERIA, criteria_for
from agents.proven_scalability.schema import (
    Block,
    BlockScores,
    Calibration,
    Evidence,
    ProvenScalabilityResult,
    Status,
    Verdict,
)

#: 3급(언론)·4급(회사 자체 발표) 근거만으로는 MET을 인정하지 않는다.
#: 원칙의 "Founder 자체 테스트만 있으면 불인정"을 코드로 강제하는 장치다.
_CREDIBLE_TIERS = frozenset({1, 2})

#: 충족 개수 → 점수. 게이트 미달 구간은 아예 키에 없다.
_SCORE_TABLE: dict[Block, dict[int, int]] = {
    "A": {1: 8, 2: 10, 3: 12},
    "B": {2: 5, 3: 7, 4: 8},
    "C": {1: 2, 2: 4, 3: 5},
}

#: 게이트 최소 충족 개수. C는 게이트가 없다.
_GATE_MINIMUM: dict[Block, int] = {"A": 1, "B": 2}

_STATUS_STRENGTH: dict[Status, int] = {"UNVERIFIABLE": 0, "NOT_MET": 1, "MET": 2}


def apply_tier_filter(evidence: list[Evidence]) -> list[Evidence]:
    """신뢰할 수 없는 출처만으로 뒷받침된 MET을 UNVERIFIABLE로 강등한다.

    강등은 MET에만 적용한다. NOT_MET은 등급과 무관하게 유지한다 —
    "언론 보도로 미달이 확인됐다"는 판정을 뒤집을 이유가 없기 때문이다.
    """
    credible: set[str] = {
        e.criterion_id
        for e in evidence
        if e.status == "MET" and e.source_tier in _CREDIBLE_TIERS
    }
    filtered: list[Evidence] = []
    for e in evidence:
        if e.status == "MET" and e.criterion_id not in credible:
            filtered.append(e.model_copy(update={"status": "UNVERIFIABLE"}))
        else:
            filtered.append(e)
    return filtered


def resolve_statuses(evidence: list[Evidence]) -> dict[str, Status]:
    """항목별 최종 상태를 확정한다. 조사되지 않은 항목은 UNVERIFIABLE이다."""
    statuses: dict[str, Status] = {c.id: "UNVERIFIABLE" for c in CRITERIA}
    for e in apply_tier_filter(evidence):
        if e.criterion_id not in statuses:
            continue  # 알 수 없는 항목 ID는 조용히 버린다
        if _STATUS_STRENGTH[e.status] > _STATUS_STRENGTH[statuses[e.criterion_id]]:
            statuses[e.criterion_id] = e.status
    return statuses


def _met_count(block: Block, statuses: dict[str, Status]) -> int:
    """statuses는 CRITERIA 10개 전부를 키로 갖는 완전한 dict여야 한다."""
    return sum(1 for c in criteria_for(block) if statuses[c.id] == "MET")


def score_block(block: Block, statuses: dict[str, Status]) -> int:
    """게이트를 넘지 못한 블록은 0점이다."""
    return _SCORE_TABLE[block].get(_met_count(block, statuses), 0)


def gate_failures(statuses: dict[str, Status]) -> list[Block]:
    return [
        block
        for block, minimum in _GATE_MINIMUM.items()
        if _met_count(block, statuses) < minimum
    ]


def decide_verdict(statuses: dict[str, Status]) -> Verdict:
    """게이트 미충족의 '원인'으로 갈린다. 커버리지 수치는 verdict를 바꾸지 않는다."""
    failed = gate_failures(statuses)
    if not failed:
        return "PASS"
    recoverable = any(
        statuses[c.id] == "UNVERIFIABLE" for b in failed for c in criteria_for(b)
    )
    return "INSUFFICIENT_EVIDENCE" if recoverable else "FAIL"


def evidence_coverage(statuses: dict[str, Status]) -> float:
    """statuses는 CRITERIA 10개 전부를 키로 갖는 완전한 dict여야 한다."""
    resolved = sum(1 for s in statuses.values() if s != "UNVERIFIABLE")
    return resolved / len(statuses)


def build_diligence_questions(
    statuses: dict[str, Status], calibration: Calibration
) -> list[str]:
    """UNVERIFIABLE 항목을 실사 질문으로 바꾼다. CRITERIA 정의 순서를 따른다.

    판정 기준 문구는 calibration.thresholds를 우선한다 — 아키타입별로
    치환된 기준이 있으면 그것을, 없으면 원칙 원문(default_threshold)을 쓴다.
    """
    return [
        f"[{c.id}] {c.label} — 공개 자료에서 확인할 수 없었다. "
        f"판정 기준: {calibration.thresholds.get(c.id, c.default_threshold)}"
        for c in CRITERIA
        if statuses[c.id] == "UNVERIFIABLE"
    ]


def score(
    evidence: list[Evidence], calibration: Calibration
) -> ProvenScalabilityResult:
    statuses = resolve_statuses(evidence)
    blocks = BlockScores(
        a=score_block("A", statuses),
        b=score_block("B", statuses),
        c=score_block("C", statuses),
    )
    return ProvenScalabilityResult(
        verdict=decide_verdict(statuses),
        score=blocks.total,
        block_scores=blocks,
        gate_failed=gate_failures(statuses),
        evidence_coverage=evidence_coverage(statuses),
        calibration=calibration,
        evidence=evidence,
        resolved_statuses=statuses,
        diligence_questions=build_diligence_questions(statuses, calibration),
    )
