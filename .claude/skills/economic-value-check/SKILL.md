---
name: economic-value-check
description: Use this skill to evaluate whether a target company's demand is Economic (not ideological) per the house's second investment principle — "임팩트 이전에 고객의 P&L을 개선하여야 한다. 고객이 환경적·사회적 당위성 때문에 구매하는 것이 아니라, 실제 경제적 효익 때문에 돈을 지불하는 기업에 투자한다." Separately validates Gate A (Customer Economic Value — cost reduction, revenue/capacity, productivity, yield/quality, asset efficiency, working capital, risk-adjusted benefit) and Gate B (Commercial Validation — paid PoC ≥2, repeat commercial customer ≥1, binding contract/PO/offtake ≥2, with DART 수주잔고·계약부채 as a fallback proxy only), runs a Subsidy/Green Premium Test ("보조금·impact를 제거해도 고객이 구매할 경제적 이유가 있는가"), and issues a verdict: PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE. Trigger when asked to check "Economic Value", "Economic, not ideological", "고객 P&L", "willingness to pay", "commercial validation", "Paid PoC와 repeat customer", "Subsidy/Green Premium", or "Why must the customer pay?". Do not trigger for generic revenue/financial analysis that doesn't ask whether demand is economic vs. ideological/subsidy-driven.
---

# Economic Value Screening

이 스킬은 하우스 투자 원칙 2번 "Economic, not ideological"을 평가한다. 이 원칙의 명제는 다음과 같다.

> 임팩트 이전에 고객의 P&L을 개선하여야 한다. 고객이 환경적·사회적 당위성 때문에 구매하는 것이 아니라, 실제 경제적 효익 때문에 돈을 지불하는 기업에 투자한다.

핵심 질문은 다음 하나로 요약된다.

> "Impact가 전혀 없다고 가정해도 고객은 경제적 이유만으로 이 제품 또는 서비스를 구매하는가?"

단순히 고객 또는 매출이 존재한다는 이유로 Economic Value가 있다고 판단하지 않는다. 다음 causal chain이 실제로 성립하는지 확인한다.

```
Customer Economic Pain → Quantifiable Economic Benefit → Willingness to Pay → Commercial Validation → Repeatability
```

중간 단계가 확인되지 않으면 추론으로 메우지 말고 Missing Evidence로 표시한다.

## 1. 입력

회사명, 제품/서비스 설명, 주요 고객, 고객 use case, IR deck, 투자검토 자료, 고객 사례, PoC 현황, 매출·계약 자료, 수주내역, PO, offtake agreement, 공급계약, 감사보고서, 사업보고서, DART 공시, 기타 공개자료·사용자 제공 자료를 입력받을 수 있다.

**정보가 부족하면 추정하거나 만들어내지 말고 Insufficient Evidence 또는 Not Disclosed로 처리한다.** 자료에 없는 ROI, payback, 고객 수, 계약 수, backlog를 만들어내지 않는다.

## 2. Gate A — Customer Economic Value

고객의 경제성을 실제로 개선하는지, 아래 7개 카테고리 중 최소 1개 이상을 확인한다. 각 카테고리는 **Confirmed / Plausible / Not Demonstrated** 중 하나로 분류하며, 최소 1개 카테고리가 **Confirmed**되어야 Gate A 핵심 요건을 충족한다.

| Category | 확인 항목 |
|---|---|
| Cost Reduction | 인건비·전력비·연료비·원재료비·유지보수비·폐기물처리비·물류비·기타 OPEX 감소 |
| Revenue / Capacity Increase | 생산량·판매량·생산 capacity·throughput 증가 |
| Productivity Improvement | 노동시간 감소, 생산속도 개선, 생산량/인력 증가, 자동화율 상승 |
| Yield / Quality Improvement | yield 상승, scrap/defect/재작업 감소, 원료 투입량 감소 |
| Asset Efficiency | uptime 증가, downtime 감소, equipment utilization·유지보수주기 개선 |
| Working Capital / Lead Time | inventory 감소, lead time 감소, 공급기간 단축, working capital 감소 |
| Risk-adjusted Benefit | supply disruption·commodity 가격변동·생산중단·규제비용·핵심원료 부족 등의 리스크로 인한 예상 경제적 손실 감소 — 단순 "리스크를 줄인다" narrative만으로는 인정하지 않고, 가능한 경우 경제적 영향(예상 손실액 등)과 연결해야 함 |

분류 기준:

- **Confirmed**: 실제 고객 데이터, 도입 전후 비교, ROI/payback/비용절감률 등으로 효익이 확인됨.
- **Plausible**: 논리는 타당하나 실제 고객 데이터·충분한 정량 근거가 없음.
- **Not Demonstrated**: 효익을 주장하지만 뒷받침할 증거가 없음.

가능한 경우 다음 KPI를 우선 정량화한다: cost saving %, annual cost saving, payback period, ROI, IRR, production increase %, yield improvement %, labor hours saved, energy cost reduction, maintenance cost reduction, downtime reduction, throughput increase. 수치가 없으면 임의로 계산·가정하지 않는다.

## 3. Gate B — Commercial Validation

Customer Economic Benefit과 별도로, "고객이 그 경제적 가치에 대해 실제로 돈을 지불했는가"를 검증한다. 다음 3가지 기준 중 **최소 1개 이상**을 충족하면 Gate B를 통과한 것으로 판단한다.

1. **Paid PoC ≥ 2건** — 서로 다른 고객·실제 산업환경에서 수행한 유상 PoC. 동일 고객의 반복 테스트를 별도 PoC로 중복 계산하지 않는다. 무료 PoC는 인정하지 않는다.
2. **Repeat Commercial Customer ≥ 1** — PoC → First Commercial Order → Repeat Purchase → Volume Expansion 패턴. 첫 구매보다 반복 구매에 더 높은 증거 가중치를 둔다.
3. **Binding Commercial Commitment ≥ 2건** — PO, binding supply agreement, binding offtake agreement, minimum purchase commitment 등. 건수만 세지 말고 질을 평가한다: legally/commercially binding 여부, 최소구매물량, 가격(산식) 존재 여부, 계약기간, 해지 용이성/penalty, qualification·financing condition 잔존 여부, 실제 구매 obligation 존재 여부. `subject to financing`, `subject to qualification`, `non-binding`, `termination at convenience`, 구매량·가격 미확정 등의 조건이 강하면 증거 수준을 낮춘다.

**LOI/MOU는 원칙적으로 Gate B의 Confirmed 조건으로 계산하지 않는다.** 시장 관심도의 보조 evidence로만 사용하고, LOI/MOU가 많다는 이유로 Gate B를 통과시키지 않는다.

## 4. DART Fallback Analysis (Proxy Commercial Evidence)

Paid PoC·repeat customer·binding contract 등 구체적 고객 데이터를 공개자료에서 확보할 수 없는 경우에만, DART 감사보고서/사업보고서 주석으로 commercial demand를 간접 검증한다. **이 데이터는 직접 Commercial Validation과 동일하게 취급하지 않는다 (Proxy로만 분류).** 가능하면 최근 3개년 추이를 분석한다.

- **수주잔고**: 절대금액, 최근 3개년 증감 추이, 매출 대비 수주잔고(Backlog/Revenue), 신규수주 증가 여부.
- **계약부채**: 최근 3개년 금액·증가율, 매출 증가율과의 관계. 회계정책·계약조건에 따라 변동될 수 있으므로 단독으로 강한 Commercial Validation으로 쓰지 않는다.
- **건설형공사계약**: EPC·플랜트·산업장비·대규모 인프라·장기 프로젝트형 사업에만 applicable. SaaS, 일반 소비재, 초기 소재 스타트업 등 프로젝트형 계약이 핵심이 아닌 기업에는 획일적으로 적용하지 않는다. Applicable한 경우 계약금액, 진행률, 수주잔액, 계약자산/계약부채, 주요 프로젝트 concentration을 검토한다.

**해석 원칙**: DART 데이터는 "실제 상업적 수요가 증가하고 있는가"를 입증하는 보조자료이며, "고객 P&L이 개선되었는가"를 직접 입증하는 자료가 아니다. **수주잔고가 증가하더라도 고객의 경제성(Gate A)이 확인되지 않으면 Economic Value 전체를 자동 PASS시키지 않는다.**

## 5. Evidence Hierarchy

Commercial evidence의 질을 다음 순서로 평가하며, 낮은 tier가 많다는 이유로 높은 tier와 동일하게 평가하지 않는다.

| Tier | 내용 |
|---|---|
| 1 — Realized Economic Validation | 반복 구매/volume expansion + 실제 ROI·cost saving·productivity 등 경제적 benefit이 동시에 확인됨 (가장 강함) |
| 2 — Binding Commercial Commitment | Binding PO, supply agreement, offtake agreement, minimum purchase commitment |
| 3 — Paid Validation | 서로 다른 고객의 Paid PoC ≥ 2 |
| 4 — Financial Statement Proxy | DART 수주잔고, 계약부채, applicable한 건설형공사계약 |
| 5 — Customer Intent | Conditional LOI, LOI, MOU, unpaid pilot |
| 6 — Narrative | management 주장, TAM, 시장 CAGR, ESG narrative (가장 약함) |

## 6. Subsidy / Green Premium Test

Gate A/B 판정과 별도로 반드시 평가한다.

> "환경적 임팩트, ESG 명분, 정부 보조금 또는 Green Premium을 제거해도 고객에게 구매할 경제적 이유가 남아 있는가?"

`Yes / Mostly Yes / Unclear / Mostly No / No` 중 하나로 판정하고 이유를 설명한다. 이 스킬에서 가장 중요한 stress test로 취급하며, subsidy 없이는 경제성이 성립하지 않는 경우 Gate A의 해당 driver를 Confirmed로 인정하지 않는다.

## 7. 최종 판정

Gate A와 Gate B를 분리 판정한 뒤 종합한다.

| 판정 | 조건 |
|---|---|
| **PASS** — Proven Economic Value | Gate A: Confirmed Customer Economic Benefit ≥ 1 **AND** Gate B: (Paid PoC ≥2 또는 Repeat Customer ≥1 또는 Binding Commitment ≥2) 중 최소 1개 충족 |
| **CONDITIONAL PASS** — Commercial Evidence but Economics Incomplete | Gate B는 통과(또는 DART proxy가 강한 추세)하지만 Gate A의 ROI/cost saving/productivity 데이터가 부족한 경우. 추가 DD 필요를 명시 |
| **FAIL** — Weak or Ideological Economics | Gate A 미확인 + 구매 이유가 ESG/명분 중심, subsidy 없으면 경제성 불성립, 무료 PoC만 반복, LOI/MOU만 다수, 실제 WTP 증거 없음 |
| **INSUFFICIENT EVIDENCE** | Customer economics, Paid PoC, repeat purchase, binding contract, DART proxy 모두 부족해 판단 자체가 어려움 (정보 부족은 FAIL과 구분) |

**Gate B(상업 증거)만으로 Gate A를 우회해 자동 PASS시키지 않는다.** Binding contract나 수주잔고 증가가 있어도 Gate A가 Confirmed되지 않으면 최대 CONDITIONAL PASS다.

## 8. 출력 형식

항상 다음 구조를 그대로 사용한다.

```
## Economic Value Verdict
Verdict: PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE
One-line Thesis: (이 회사가 왜 경제적 이유만으로 고객의 구매를 유도할 수 있는지/없는지 한 문장)

## 1. Customer Economic Value (Gate A)
| Economic Driver | Status | Evidence | P&L Impact |
| Cost Reduction | Confirmed/Plausible/Not Demonstrated/N/A | … | … |
| Revenue / Capacity Increase | … | … | … |
| Productivity Improvement | … | … | … |
| Yield / Quality | … | … | … |
| Asset Efficiency | … | … | … |
| Working Capital | … | … | … |
| Risk-adjusted Benefit | … | … | … |

## 2. Commercial Validation (Gate B)
| Criterion | Result | Evidence Tier | Evidence |
| Paid PoC ≥ 2 | Yes/No/Unknown | … | … |
| Repeat Commercial Customer ≥ 1 | Yes/No/Unknown | … | … |
| Binding Contract/PO/Offtake ≥ 2 | Yes/No/Unknown | … | … |

## 3. Customer Economics
Customer cost saving: … / Revenue·productivity benefit: … / Payback period: … / ROI·IRR: … / Other measurable economics: …
(확인 안 되는 항목은 Not Disclosed)

## 4. DART Proxy Analysis
(직접 데이터가 충분하면 짧게. 부족하면 최근 3개년)
| Metric | Y-2 | Y-1 | Latest | Trend | Interpretation |
| Revenue | | | | | |
| Order Backlog | | | | | |
| Backlog / Revenue | | | | | |
| Contract Liabilities | | | | | |
| Construction Contract-related Metric (if applicable) | | | | | |

## 5. Subsidy / Green Premium Test
Rating: Yes / Mostly Yes / Unclear / Mostly No / No
(보조금·impact 제거 시에도 구매 이유가 남는지 설명)

## 6. Evidence Hierarchy
(확인된 evidence를 Tier별로 정리, 가장 강한 evidence 3~5개 우선 표시)

## 7. Missing Evidence / DD Questions
(최대 5개, 경영진/고객에게 실제로 물을 수 있을 정도로 구체적으로)

## 8. IC Conclusion
Why must the customer pay? (제품이 좋다/시장이 성장한다는 설명 금지 — 실제 경제적 이익과 이를 증명하는 commercial behavior를 연결해 2~3문장)
```

## 9. 분석 원칙 (필수 준수)

- **Do not confuse revenue with economic value.** 매출 존재가 고객 P&L 개선의 증거는 아니다.
- **Do not confuse PoC with commercial adoption.** PoC는 검증 단계이며, 실제 구매·반복구매보다 낮은 evidence다.
- **Do not confuse LOI with revenue.** LOI/MOU는 intent evidence이며 binding purchase와 구분한다.
- **Do not overvalue backlog.** 수주잔고는 commercial demand의 proxy일 뿐 고객 경제성의 직접 증거가 아니다.
- **Require causality.** Economic Problem → Economic Improvement → Customer Payment → Repeatability 연결고리를 항상 확인하고, 끊긴 단계는 Missing Evidence로 표시한다.
- **Never fabricate missing data.** 자료에 없는 ROI, payback, 고객 수, 계약 수, backlog를 만들어내지 않는다. 정보가 없으면 Not Disclosed / Unknown / Insufficient Evidence로 표시한다.
