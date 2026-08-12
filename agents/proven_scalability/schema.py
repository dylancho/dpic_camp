"""Proven Scalability 에이전트의 데이터 계약.

이 모듈에는 LLM 호출이 없다. 순수 데이터 정의만 둔다.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Status = Literal["MET", "NOT_MET", "UNVERIFIABLE"]
Verdict = Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"]
Block = Literal["A", "B", "C"]

#: 1 = DART 공시·감사보고서 주석·등록특허 원문·거래소 기술성 평가
#: 2 = 제3자 공인 시험성적서·독립 인증기관·peer-reviewed 논문
#: 3 = 언론 보도·산업 리포트
#: 4 = 회사 자체 발표·IR 자료·홈페이지
SourceTier = Annotated[int, Field(ge=1, le=4)]


class Evidence(BaseModel):
    """한 항목에 대한 하나의 근거. 리서처가 반환하는 유일한 타입."""

    criterion_id: str
    status: Status = Field(
        description=(
            "리서처가 수집 시점에 매긴 상태 (필터 이전, 감사 추적용). "
            "등급 필터·다중 근거 병합을 거치지 않았으므로 최종 판정과 다를 수 있다 — "
            "예: tier 3 근거 하나만으로 MET을 매겼어도 scoring.score()가 신뢰 등급 미달로 "
            "UNVERIFIABLE로 강등할 수 있다. 항목별 최종 상태는 "
            "ProvenScalabilityResult.resolved_statuses를 봐야 한다."
        )
    )
    source_tier: SourceTier
    source_url: str | None = None
    quote: str = Field(description="판단 근거가 된 원문 인용")
    extracted_value: str | None = Field(
        default=None,
        description="PoC 건수·가동시간·특허 건수·석사 비중 등 정량값. 원문 표기 그대로",
    )


class Calibration(BaseModel):
    """PM 에이전트가 내려준 아키타입과 임계치. 본 에이전트는 분류하지 않는다."""

    archetype: str
    thresholds: dict[str, str] = Field(default_factory=dict)
    injected: bool = Field(
        description="False면 PM 주입 없이 아키타입 중립 기준으로 실행됐다는 뜻"
    )
    note: str | None = None


class BlockScores(BaseModel):
    a: int = Field(ge=0, le=12)
    b: int = Field(ge=0, le=8)
    c: int = Field(ge=0, le=5)

    @property
    def total(self) -> int:
        return self.a + self.b + self.c


class ProvenScalabilityResult(BaseModel):
    verdict: Verdict
    score: int = Field(ge=0, le=25)
    block_scores: BlockScores
    gate_failed: list[Block]
    evidence_coverage: float = Field(
        ge=0.0, le=1.0, description="조사 항목 중 UNVERIFIABLE이 아닌 비율"
    )
    calibration: Calibration
    evidence: list[Evidence] = Field(
        description=(
            "리서처가 수집한 근거 원문 그대로 (필터 이전, 감사 추적용). 개별 Evidence.status는 "
            "등급 필터·다중 근거 병합 이전 값이라 최종 판정과 어긋날 수 있다 — 점수 산출에 쓰인 "
            "항목별 최종 상태는 resolved_statuses를 볼 것."
        )
    )
    resolved_statuses: dict[str, Status] = Field(
        default_factory=dict,
        description=(
            "항목(criterion_id)별 최종 상태 — 등급 필터와 다중 근거 병합을 거친, 점수 산출에 "
            "실제로 쓰인 값. 이 필드가 권위 있는 소스다. evidence[i].status와 다를 수 있다. "
            "scoring.score()가 채운다 (CRITERIA 10개 전부를 키로 갖는다)."
        ),
    )
    diligence_questions: list[str]
