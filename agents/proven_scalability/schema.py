"""Proven Scalability 에이전트의 데이터 계약.

이 모듈에는 LLM 호출이 없다. 순수 데이터 정의만 둔다.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field

Status = Literal["MET", "NOT_MET", "UNVERIFIABLE"]
Verdict = Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"]
Block = Literal["A", "B", "C"]

#: 1 = DART 공시·감사보고서 주석·등록특허 원문·거래소 기술성 평가
#: 2 = 제3자 공인 시험성적서·독립 인증기관·peer-reviewed 논문
#: 3 = 언론 보도·산업 리포트
#: 4 = 회사 자체 발표·IR 자료·홈페이지
SourceTier = Annotated[int, Field(ge=1, le=4)]

#: 아키타입이 주입되지 않았을 때 쓰는 마커. 설계 §2.4 — 자체 추정하지 않고
#: 중립 기준으로 실행하되 그 사실을 결과에 명시한다.
UNCALIBRATED = "uncalibrated"


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
    """PM 에이전트가 내려준 아키타입과 임계치. 본 에이전트는 분류하지 않는다.

    '아키타입이 주입됐는가'와 '항목별 임계치 오버라이드가 주입됐는가'는 서로 다른
    질문이다. 둘을 한 불리언에 담으면 `--archetype materials`(오버라이드 없음)
    실행이 전부 '미보정'으로 잘못 표시되고, 프롬프트가 materials 임계치를 보여주면서
    "이건 중립 기준이다"라고 리서처에게 거짓을 말하게 된다. 그래서 나눠 둔다.

    설계 §2.4의 `uncalibrated` 마커는 **아키타입이 없다**는 뜻이지
    항목별 오버라이드가 없다는 뜻이 아니다.
    """

    archetype: str
    thresholds: dict[str, str] = Field(default_factory=dict)
    thresholds_injected: bool = Field(
        default=False,
        description=(
            "PM이 항목별 임계치 오버라이드를 직접 내려줬는가. 아키타입 오버라이드 테이블 "
            "적용은 여기 포함되지 않는다"
        ),
    )
    note: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def archetype_injected(self) -> bool:
        """PM이 아키타입을 내려줬는가. False면 아키타입 중립 기준으로 실행됐다는 뜻.

        archetype에서 파생한다 — 별도 필드로 두면 둘이 어긋날 수 있고, 어긋나는 쪽이
        정확히 이번에 고친 버그였다.
        """
        return self.archetype != UNCALIBRATED


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
