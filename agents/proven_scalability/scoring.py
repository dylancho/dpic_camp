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

#: 현재 정책(2026-08-13, 프로젝트 오너 결정): 1~4급 전부 MET을 뒷받침할 수 있다.
#:
#: 원래는 {1, 2}였다 — 3급(언론)·4급(회사 자체 발표)만으로는 MET을 인정하지 않아
#: 원칙의 "Founder 자체 테스트만 있으면 불인정"을 코드로 강제했다. 그런데 비상장
#: pre-IPO 기업의 공개 근거는 거의 전부 3~4급이라, 그 필터를 적용하면 모든 항목이
#: 강등되어 서로 전혀 다른 기업들이 똑같이 0/25로 나왔다 (범한메카텍·제이알에너지솔루션
#: 실측 사례). 오너에게 원칙 문구와의 충돌을 명시적으로 알렸고, 그럼에도 4개 등급 전부
#: 허용하기로 결정했다 — 이 파일의 판단이 아니라 그 결정을 반영한 것이다.
#:
#: 강등 메커니즘 자체(apply_tier_filter)는 지우지 않았다. 이 상수를 다시 {1, 2}로
#: (또는 다른 부분집합으로) 좁히기만 하면 정책을 즉시 원복할 수 있다.
#: 하지만 정책이 넓어진 만큼 스코어의 근거 구성을 투명하게 드러내는 책임이
#: ProvenScalabilityResult.met_tier_profile과 CLI 출력으로 넘어갔다 — score() 참고.
_CREDIBLE_TIERS = frozenset({1, 2, 3, 4})

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


def met_tier_profile(
    evidence: list[Evidence], statuses: dict[str, Status]
) -> dict[str, int]:
    """MET으로 확정된 항목마다, 그 MET을 뒷받침한 가장 강한(숫자가 작은) 등급을 기록한다.

    statuses는 이미 resolve_statuses가 확정한 최종 상태다 — 여기서 다시 상태 로직을
    계산하지 않는다. 이 함수는 그 결과 중 MET인 항목에 대해서만, 원본 evidence를
    훑어 가장 신뢰도 높은 근거 등급을 찾는다. tier 1~2만 신뢰하던 시절에는 이 정보가
    apply_tier_filter의 강등 여부로 암묵적으로 드러났지만, 지금은 4개 등급이 전부
    MET을 뒷받침할 수 있어 그 신호가 사라졌다 — 그래서 명시적으로 기록한다.
    """
    profile: dict[str, int] = {}
    for e in evidence:
        if e.status != "MET" or statuses.get(e.criterion_id) != "MET":
            continue
        current = profile.get(e.criterion_id)
        if current is None or e.source_tier < current:
            profile[e.criterion_id] = e.source_tier
    return profile


def unknown_criterion_ids(evidence: list[Evidence]) -> list[str]:
    """resolve_statuses가 버릴 항목 ID를 미리 뽑는다. 정의 순서가 아니라 사전순."""
    known = {c.id for c in CRITERIA}
    return sorted({e.criterion_id for e in evidence if e.criterion_id not in known})


def score(
    evidence: list[Evidence],
    calibration: Calibration,
    research_notes: list[str] | None = None,
) -> ProvenScalabilityResult:
    """점수는 evidence와 calibration만으로 결정된다.

    research_notes는 배점에 전혀 관여하지 않는다 — 조사가 온전했는지에 대한 기록을
    결과에 실어 보내기만 한다. 커버리지가 낮을 때 그것이 '찾아봤지만 없었다'인지
    '끝까지 못 봤다'인지를 상위 에이전트가 구분할 수 있어야 하기 때문이다.
    """
    notes = list(research_notes or [])
    dropped = unknown_criterion_ids(evidence)
    if dropped:
        notes.append(
            f"알 수 없는 항목 ID {len(dropped)}건을 버렸다: {', '.join(dropped)}. "
            "커버리지 하락이 추출 오류 때문일 수 있으니 그대로 신뢰하지 말 것."
        )

    statuses = resolve_statuses(evidence)
    blocks = BlockScores(
        a=score_block("A", statuses),
        b=score_block("B", statuses),
        c=score_block("C", statuses),
    )
    tier_profile = met_tier_profile(evidence, statuses)
    weak_only = sorted(
        criterion_id for criterion_id, tier in tier_profile.items() if tier >= 3
    )
    if weak_only:
        notes.append(
            f"MET {len(weak_only)}건이 3~4급(언론·회사 자체 발표) 근거에만 의존한다: "
            f"{', '.join(weak_only)}. 1~2급 근거로 보강되기 전까지는 실사에서 재확인할 것."
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
        met_tier_profile=tier_profile,
        research_notes=notes,
        diligence_questions=build_diligence_questions(statuses, calibration),
    )
