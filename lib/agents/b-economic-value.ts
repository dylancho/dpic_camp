/**
 * 원칙 b — Economic Value (시장성, 25점)
 *
 * "임팩트 이전에 고객의 P&L을 개선하여야 한다."
 * 이 에이전트의 존재 이유는 단 하나 — 홍보성 파트너십과 실제 매출을 구분하는 것.
 */

import type { PrincipleAgent } from '../contract';
import { runPrincipleAgent } from './runtime';

const EXTRA_GUIDANCE = `
## 상업 증거 티어 판정 (ev.tier) — 가장 배점이 큰 항목이다
아래를 **엄격히** 구분한다. 애매하면 낮은 티어로 내린다.

인정하지 않는 것 (전부 level 0 기여):
  MOU, LOI, 업무협약, 전략적 파트너십, 공동개발 의향, 수상 이력,
  정부 R&D 과제 선정, 데모데이 입상, "협의 중", "논의 중", "예정"

인정하는 것:
  - 유상 PoC: 고객이 **돈을 내고** 진행한 실증. 서로 다른 고객·실제 산업환경 조건.
  - 반복 구매 Commercial Customer: 2회 이상 발주한 상업 고객.
  - Binding contract / PO / off-take: 구속력 있는 계약. 금액·기간·물량이 특정된다.
  - DART 주석: 수주잔고 / 계약부채 / 건설형공사계약 항목의 **추이**.
    ↑ 위 1~3을 확인할 수 없을 때의 대체 경로다. 절대 금액보다 **증가 추세**를 본다.
    계약부채 증가 = 선수금 유입 = 고객이 먼저 돈을 냈다는 뜻이므로 강한 신호다.

paidEvidenceCount에는 위 인정 항목의 총 건수를 담는다 (MOU/LOI는 세지 않는다).

## 고객 ROI · Payback (ev.roi)
핵심 질문: "고객이 이걸 사면 몇 년 만에 회수되는가."
자사 매출 성장률·영업이익률은 여기서 답이 아니다. **고객의** P&L이어야 한다.
Calibration의 paybackThresholdYears 이내여야 level 2.
수치가 없고 "비용을 크게 절감"류 문구만 있으면 level 1을 넘지 못한다.

## Willingness to pay (ev.wtp)
유상 전환율(무상 PoC → 유상), 반복 구매, 계약부채·선수금 증가 세 가지로 본다.
전체 PoC 중 무상 비중이 지배적이면 level 0.

## 공통
매출 숫자를 인용할 때는 반드시 **기간과 출처**를 함께 적는다.
연결/별도, 감사受 여부가 불분명하면 rationale에 그 불확실성을 적는다.
`.trim();

export const economicValueAgent: PrincipleAgent = (input) =>
  runPrincipleAgent('economic_value', input, { extraGuidance: EXTRA_GUIDANCE });
