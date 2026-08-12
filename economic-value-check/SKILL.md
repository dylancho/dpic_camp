---
name: economic-value-check
description: Use this skill to evaluate a pre-IPO/climate-tech target company against the house investment framework's "Economic Value" principle — whether the company improves customer P&L before any impact narrative counts. Checks paid PoC records, repeat commercial customers, binding contracts/PO/offtake, and (as a fallback) DART 감사보고서 주석의 수주잔고·계약부채·건설형공사계약 추이. Produces a gate result (pass/fail on "최소 1개 이상 존재"), an evidence-tier classification, and a 25점 만점 score (상업 증거 티어 13 · 고객 ROI·Payback 8 · Willingness to Pay 4) for use in the house Score Pad. Trigger when asked to check "Economic Value", "고객 P&L", "PoC 증거", "상업 증거 티어", "수주잔고", or to score a company on the house investment scorecard's market-fit/economic-value axis.
---

# Economic Value Check

이 스킬은 하우스 투자 원칙 2번 "Economic Value (시장성)"를 평가한다. 이 원칙의 명제는 다음과 같다.

> "임팩트 이전에 고객의 P&L을 개선하여야 한다."

이 스킬은 임팩트 서사나 기술 우수성과 무관하게, 실제 고객이 돈을 냈거나 돈을 낼 만큼 경제적 이득을 봤다는 "상업적 증거"만을 근거로 판단한다. 증거가 없으면 감점하고, 증거가 약하면 낮은 티어로 채점한다. 서술형 주장("고객이 만족한다", "시장 반응이 좋다")은 증거로 인정하지 않는다.

## 1. 게이트 조건 (통과/탈락)

다음 네 가지 중 **최소 1개 이상**이 존재해야 이 원칙을 통과한다. 하나도 없으면 Economic Value 원칙은 게이트 실패이며, 이 사실을 최상단에 명시한다.

1. 서로 다른 고객·서로 다른 실제 산업환경에서 진행한 **유상 PoC ≥ 2건**
2. 반복 구매하는 **Commercial Customer ≥ 1**
3. **Binding contract / PO / offtake ≥ 2건**
4. 위 1~3에 해당하는 데이터를 구할 수 없는 경우에 한해, **DART 감사보고서 주석**에 명시된 수주잔고·계약부채·건설형공사계약 항목의 최근 추이로 판단(대체 증거, 하위 항목 참고)

각 조건을 확인할 때는 다음을 반드시 구분해서 기록한다.

- MOU, LOI, 비구속적 양해각서는 증거로 **인정하지 않는다** (0점 처리).
- "유상"인지 "무상"인지 반드시 확인한다. 무상 PoC는 관심의 증거이지 경제적 가치의 증거가 아니다.
- "서로 다른 고객/환경"인지 확인한다. 동일 고객사의 반복 테스트는 재현성 증거는 될 수 있어도 시장 검증 증거로는 약하다.

## 2. 데이터 수집 체크리스트

평가에 필요한 원자료를 아래 우선순위로 요청·조회한다.

1. **1차 자료(회사 제공)**: PoC 계약서/견적서(유상 여부와 금액 확인), 고객사 리스트와 각 고객의 최초 구매일·재구매 이력, 바인딩 계약서·PO·offtake 계약의 사본 또는 요약(계약 기간, 물량, 가격 조항)
2. **공개 자료(교차검증)**: DART 전자공시시스템에서 해당 법인명 또는 계열 법인명으로 감사보고서를 조회하고, 주석 중 "수주잔고", "계약부채", "건설형공사계약" 또는 이에 상응하는 계정과목을 최근 2~3개년 비교
3. **직접 검증(선택, 확신도가 낮을 때)**: 고객사 레퍼런스콜을 통해 구매 동기와 재구매 의사를 확인

데이터가 전혀 없는 항목은 "0점"이 아니라 "**데이터 부족 — 확인 필요**"로 표시하고, 어떤 문서를 요청해야 하는지 구체적으로 적는다. 없는 데이터를 추정해서 점수를 매기지 않는다.

## 3. 점수화 (25점 만점)

하우스 Score Pad의 배점 구조를 그대로 따른다.

### 3-1. 상업 증거 티어 (13점)
증거를 아래 티어 사다리 중 가장 높이 도달한 단계로 분류하고 해당 점수를 부여한다. 여러 조건을 동시에 충족해도 최고 티어 점수만 인정한다(중복 가산 없음).

| 티어 | 조건 | 배점 |
|---|---|---|
| 0 | MOU/LOI만 존재, 또는 증거 없음 | 0 |
| 1 | 무상 PoC만 존재 | 2 |
| 2 | 유상 PoC ≥ 2건 (서로 다른 고객·환경) | 6 |
| 3 | 반복 구매 Commercial Customer ≥ 1 | 9 |
| 4 | Binding contract/PO/offtake ≥ 2건 | 13 |
| 대체 | DART 수주잔고·계약부채·건설형공사계약이 최근 2~3개년 뚜렷한 증가 추세 | 6~9 (추세 강도에 따라 판단, 상한 9) |

DART 대체 증거는 직접 증거(고객명, 계약조건 확인 가능)보다 확신도가 낮으므로 원칙적으로 9점을 넘기지 않는다. 이 상한을 넘기려면 반드시 1~3의 직접 증거가 함께 있어야 한다.

### 3-2. 고객 ROI·Payback 임계 충족 (8점)
고객이 이 제품/서비스 도입으로 얻는 투자회수기간(payback) 또는 ROI 데이터가 있는지 확인한다.

- Payback 데이터가 있고 해당 산업 평균 이하 또는 2년 이내: 8점
- Payback 데이터는 있으나 임계치를 초과하거나 산업 평균보다 느림: 4점
- Payback/ROI 데이터 자체가 없음: 0점 (추정치로 대체하지 말 것)

### 3-3. Willingness to Pay (4점)
고객이 실제로 지불 의사를 행동으로 보였는지 확인한다. 유상 PoC 비용 규모, 재구매율, 계약부채 증가 추세 등을 근거로 삼는다.

- 유상 PoC 단가가 시장 통상 수준 이상이거나, 재구매율이 확인되거나, 계약부채가 최근 분기·연도 대비 증가: 4점
- 부분적으로만 확인됨(예: 유상이지만 금액이 상징적 수준): 2점
- 확인 불가: 0점

## 4. 출력 형식

다음 구조로 결과를 제시한다.

```
[Economic Value 게이트] Pass / Fail — 근거: (충족한 조건 번호와 구체 수치)
[증거 티어] 0~4 중 (티어명) — 근거: (고객명/계약 형태/DART 계정과목 등, 익명화 필요시 "고객 A" 식으로 표기)
[점수] 상업증거티어 _/13 · ROI·Payback _/8 · WTP _/4 → 합계 _/25
[데이터 갭] 확인하지 못한 항목과 요청할 문서 목록
[한 줄 코멘트] 이 기업이 임팩트 이전에 실제로 고객의 손익을 개선한다고 볼 수 있는 근거 요약 (한 문장, 서술형 주장 아닌 수치 기반)
```

## 5. 주의사항

- 창업자·회사가 제공한 정성적 주장("고객 반응이 좋다", "시장이 원한다")은 절대 점수 근거로 쓰지 않는다.
- 서로 다른 산업/고객 조건을 만족하는지 반드시 확인한다. 계열사·관계사 간 거래는 독립적 상업 증거로 인정하지 않는다.
- DART 데이터를 쓸 때는 반드시 조회 시점과 대상 계정과목명을 그대로 인용한다(계정과목명은 기업마다 다를 수 있음).
- 이 스킬은 하우스 Score Pad 4대 원칙 중 하나(Economic Value, 25/100점)만 평가한다. 최종 Pass/Watchlist/Fast-track 판정은 Structural Demand, Physical Impact, Proven Scalability 점수와 합산한 뒤 cut-off 규칙(하드 게이트, 편중 방지 플로어)까지 적용해야 나온다.
