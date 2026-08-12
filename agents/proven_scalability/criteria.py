"""하우스 투자 원칙 (d)의 판정 항목과 아키타입별 임계치.

**항목**(무엇을 보는가)과 **임계치 문구**(얼마면 충족인가)는 이 파일이 원본이다.
아키타입 치환도 여기서 끝난다.

하지만 '하우스 기준'의 나머지 절반은 여기 없다. 바꿀 때 함께 봐야 하는 자리:

- 충족 개수 → 점수 표, 게이트 최소 개수 → `scoring.py` (_SCORE_TABLE, _GATE_MINIMUM)
- 블록별 상한(12·8·5) → `schema.py` BlockScores의 Field 범위
- CLI 출력의 `/12 · /8 · /5` 리터럴 → `__main__.py`

한 군데로 합치지 않은 이유는 각자 다른 계약을 지키기 때문이다 — schema는 직렬화
경계의 검증, scoring은 판정 로직, CLI는 표시. 대신 이 목록을 여기 남겨 둔다.
항목 ID 집합의 원본은 `schema.CriterionId`다 (Evidence의 JSON 스키마 enum이 되어야 하므로).
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.proven_scalability.schema import (
    CRITERION_IDS,
    UNCALIBRATED,
    Block,
    Calibration,
    CriterionId,
)


@dataclass(frozen=True)
class Criterion:
    id: CriterionId
    block: Block
    label: str
    default_threshold: str


CRITERIA: tuple[Criterion, ...] = (
    # (A) 기술 작동 증명 — 게이트 1개 이상
    Criterion(
        "A1_poc_reproducibility",
        "A",
        "PoC 재현성",
        "서로 다른 고객·환경에서 PoC 2회 이상, 핵심 성능 KPI가 ±10~20% 내 재현",
    ),
    Criterion(
        "A2_third_party_validation",
        "A",
        "제3자 검증",
        "제3자 시험성적서 또는 독립 인증 2건 이상 (Founder 자체 테스트만 있으면 불인정)",
    ),
    Criterion(
        "A3_field_operation_hours",
        "A",
        "실환경 가동",
        "실환경 누적 가동 1,000시간 이상",
    ),
    # (B) 해자 — 게이트 2개 이상
    Criterion(
        "B1_exchange_tech_grade",
        "B",
        "거래소 기술성 평가",
        "거래소 기술성 평가 A 이상 (기술특례상장 기준 등급)",
    ),
    Criterion(
        "B2_registered_patents",
        "B",
        "등록 특허",
        "등록 특허 3건 이상 (출원 아님). 핵심 청구항의 경쟁사 회피 난이도를 함께 본다",
    ),
    Criterion(
        "B3_domain_expertise",
        "B",
        "도메인 전문성",
        "관련 도메인 석사 이상 인력 비중 60% 이상",
    ),
    Criterion(
        "B4_lab_publication_track",
        "B",
        "랩·논문 이력",
        "핵심 인력이 관련 도메인 랩실 근무 이력, peer-reviewed 논문, 또는 핵심 특허를 보유",
    ),
    # (C) Scale-up 준비 — 게이트 없음
    Criterion(
        "C1_capacity_plan",
        "C",
        "생산능력 확대 계획",
        "라인·플랜트 증설 로드맵이 시점과 규모로 제시된다",
    ),
    Criterion(
        "C2_capex_funding",
        "C",
        "capex 조달 계획",
        "증설에 필요한 자금의 출처가 특정된다 (조달 완료 또는 확정 계획)",
    ),
    Criterion(
        "C3_supply_chain",
        "C",
        "공급망 확보",
        "핵심 원료·부품의 공급 계약 또는 이중 소싱이 확보되어 있다",
    ),
)

#: ID 집합의 원본은 schema.CriterionId다 (Evidence의 JSON 스키마 enum이 되어야 하므로).
#: 임포트 시점에 두 정의가 정확히 일치하는지 확인한다 — 어긋난 채로 굴러가면
#: Evidence는 통과하는데 scoring이 버리는 ID가 생긴다.
assert tuple(c.id for c in CRITERIA) == CRITERION_IDS, (
    "criteria.CRITERIA와 schema.CriterionId가 어긋났다. schema.CriterionId를 고칠 것"
)

#: 아키타입별로 원칙의 문구를 치환한다. 여기 없는 항목은 default_threshold를 쓴다.
ARCHETYPE_OVERRIDES: dict[str, dict[str, str]] = {
    "deep_tech": {
        "A3_field_operation_hours": (
            "Pilot plant 가동 + TRL 6 이상"
        ),
        "A2_third_party_validation": "제3자 검증 2건 이상 (장기 validation 허용)",
    },
    "materials": {
        "A1_poc_reproducibility": "Pilot run 2회 이상 + 고객 qualification 1건 이상, 재현성 ±10~20%",
        "A3_field_operation_hours": "Pilot run 누적 검증. 시간 기준 대신 배치 수와 수율 재현성으로 본다",
    },
    "industrial_hardware": {},  # 원칙 원문이 곧 하드웨어 기준이다
    "energy_infra": {
        "A3_field_operation_hours": "실증 사이트 가동 + 성능보증(PPA 또는 성능계약) 체결",
    },
    "recycling": {
        "A1_poc_reproducibility": "파일럿 recovery rate 검증 2회 이상",
        "A3_field_operation_hours": "파일럿 플랜트 누적 처리량과 recovery rate 재현성",
    },
    "software_ai_robotics": {
        "A1_poc_reproducibility": "서로 다른 환경에 배포 2건 이상, 핵심 성능 재현",
        "A3_field_operation_hours": "프로덕션 배포 후 운영 기간과 uptime. 가동시간 기준을 적용하지 않는다",
        "C1_capacity_plan": "인프라 확장 계획 (트래픽 증가에 대한 아키텍처·비용 대응)",
        "C2_capex_funding": "조직·인력 확장 계획 (채용 규모와 자금 출처)",
        "C3_supply_chain": "재현 가능한 배포 파이프라인 (CI/CD, 롤백, 모니터링)",
    },
}

_UNCALIBRATED_NOTE = (
    "PM 에이전트의 아키타입 임계치가 주입되지 않아 원칙 원문의 중립 기준으로 실행했다. "
    "산업 특성이 반영되지 않았으므로 점수를 그대로 신뢰하지 말 것."
)


def criteria_for(block: Block) -> tuple[Criterion, ...]:
    return tuple(c for c in CRITERIA if c.block == block)


def criterion_ids() -> frozenset[str]:
    return frozenset(c.id for c in CRITERIA)


def resolve_thresholds(
    archetype: str | None, injected: dict[str, str] | None
) -> Calibration:
    """적용할 임계치를 확정한다.

    우선순위는 PM 주입값 > 아키타입 오버라이드 > 원칙 원문이다.
    아키타입이 없으면 자체 추정하지 않고 중립 기준으로 실행하되 그 사실을 명시한다.
    """
    thresholds = {c.id: c.default_threshold for c in CRITERIA}

    if archetype is None:
        return Calibration(
            archetype=UNCALIBRATED,
            thresholds=thresholds,
            thresholds_injected=False,
            note=_UNCALIBRATED_NOTE,
        )

    thresholds.update(ARCHETYPE_OVERRIDES.get(archetype, {}))
    note = None
    if archetype not in ARCHETYPE_OVERRIDES:
        note = f"알 수 없는 아키타입 '{archetype}' — 원칙 원문의 중립 기준을 적용했다."
    if injected:
        thresholds.update(injected)

    return Calibration(
        archetype=archetype,
        thresholds=thresholds,
        thresholds_injected=bool(injected),
        note=note,
    )
