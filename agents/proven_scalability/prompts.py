"""리서처 프롬프트. 조사용과 추출용이 분리되어 있다."""

from __future__ import annotations

from agents.proven_scalability.criteria import criteria_for
from agents.proven_scalability.schema import Block, Calibration

_BLOCK_LABEL: dict[Block, str] = {
    "A": "기술 작동 증명",
    "B": "해자 (Defensibility)",
    "C": "Scale-up 준비",
}

_RESEARCH_TEMPLATE = """\
너는 pre-IPO 기업 투자 심사의 기술성 리서처다. 담당 블록은 **({block}) {block_label}**이다.

대상 기업: {company}
적용 아키타입: {archetype}{calibration_note}

## 조사할 항목

{criteria_block}

## 하는 일

각 항목에 대해 공개 자료에서 근거를 찾는다. 툴은 다음을 쓴다.

- `dart_search` — DART 공시·감사보고서 주석. 비상장은 공시 의무가 없어 결과가 없을 수 있다
- `web_search` — 제3자 인증, peer-reviewed 논문, 언론 보도
- `patent_search` — 특허 조회 (현재 키 미확보 상태)

## 하지 않는 일

- **점수를 세지 마라.** 몇 개가 충족됐는지 계산하지 마라. 그건 코드가 한다
- **게이트 통과 여부를 판정하지 마라.** 최종 결론을 내리지 마라
- **근거 없이 추정하지 마라.** 못 찾았으면 못 찾았다고 하는 것이 정답이다

## 보고

조사가 끝나면 항목별로 다음을 정리해 답한다.

- 찾은 근거의 출처(URL 또는 공시 접수번호)와 원문 인용
- 인용에 담긴 정량값 (PoC 건수·가동시간·특허 건수·인력 비중 등)
- 그 출처가 공시인지, 제3자 인증인지, 언론 보도인지, 회사 자체 발표인지
- 근거를 찾지 못한 항목은 "찾지 못함"이라고 명시
"""

_UNCALIBRATED_LINE = (
    "\n\n**주의**: PM 에이전트의 아키타입 임계치가 주입되지 않았다. "
    "아래는 하우스 원칙 원문의 중립 기준이다. 산업 특성에 맞게 임의로 완화하거나 "
    "강화하지 말고, 이 기준 그대로 조사하라."
)

EXTRACTION_SYSTEM = """\
너는 조사 기록을 구조화된 근거 목록으로 변환한다. 새로 조사하지 않고, 주어진 기록에 \
있는 내용만 사용한다.

## 상태 판정

- `MET` — 근거를 찾았고 임계치를 충족한다
- `NOT_MET` — 근거를 찾았으나 임계치에 미달한다
- `UNVERIFIABLE` — 판정할 근거를 찾지 못했다

**`UNVERIFIABLE`과 `NOT_MET`을 혼동하지 마라.** 자료를 못 찾은 것과 자료를 찾았는데 \
기준에 못 미치는 것은 전혀 다른 정보다.

## 출처 등급

- 1급 — DART 공시, 감사보고서 주석, 등록 특허 원문, 거래소 기술성 평가
- 2급 — 제3자 공인 시험성적서, 독립 인증기관, peer-reviewed 논문
- 3급 — 언론 보도, 산업 리포트
- 4급 — 회사 자체 발표, IR 자료, 홈페이지

등급은 있는 그대로 매긴다. 하위 계층 코드가 3~4급 단독 근거를 자동으로 강등하므로, \
등급을 올려 적어 도와주려 하지 마라.

## 규칙

- 한 항목에 근거가 여럿이면 Evidence를 여러 개 만든다
- `quote`는 반드시 기록에 실제로 있는 원문이어야 한다. 요약하거나 지어내지 마라
- 근거를 못 찾은 항목도 `UNVERIFIABLE`로 반드시 포함한다
"""

_EXTRACTION_TEMPLATE = """\
다음은 ({block}) 블록의 조사 기록이다.

## 대상 항목

{criteria_ids}

## 조사 기록

{transcript}

위 기록을 Evidence 목록으로 변환하라. 대상 항목 전부에 대해 최소 하나씩 만든다.
"""


def research_prompt(block: Block, company: str, calibration: Calibration) -> str:
    lines = []
    for criterion in criteria_for(block):
        # scoring.build_diligence_questions와 같은 폴백을 쓴다. Calibration은 PM
        # 에이전트와의 주입 계약이고 그 포맷이 아직 미확정이라(설계 §7.4),
        # thresholds가 비어 오는 Calibration도 정상 입력으로 받아야 한다.
        threshold = calibration.thresholds.get(criterion.id, criterion.default_threshold)
        lines.append(f"### {criterion.id} — {criterion.label}\n판정 기준: {threshold}")

    # 경고는 '아키타입이 없다'에만 붙인다. 항목별 오버라이드 유무로 판단하면
    # 아키타입 임계치를 보여주면서 "중립 기준이다"라고 거짓말하게 된다.
    return _RESEARCH_TEMPLATE.format(
        block=block,
        block_label=_BLOCK_LABEL[block],
        company=company,
        archetype=calibration.archetype,
        calibration_note="" if calibration.archetype_injected else _UNCALIBRATED_LINE,
        criteria_block="\n\n".join(lines),
    )


def extraction_prompt(block: Block, transcript: str) -> str:
    return _EXTRACTION_TEMPLATE.format(
        block=block,
        criteria_ids="\n".join(
            f"- `{c.id}` — {c.label}" for c in criteria_for(block)
        ),
        transcript=transcript,
    )
