---
name: structural-demand-check
description: Use this skill to evaluate whether a target company's demand is Structural (not cyclical) per the house's first investment principle — "정책이나 유행에 의해 일시적으로 만들어진 수요가 아니라, 기업의 경제적 의사결정을 바꾸는 비가역적이고 장기적인 산업 변화에서 발생하는 수요에 투자한다." Maps demand sources onto 5 structural drivers (Resource Constraint, Cost Curve Shift, Infrastructure Replacement Cycle, Supply Chain Reconfiguration, Productivity Imperative), classifies each driver's evidence as Confirmed/Plausible/Not Demonstrated, runs a Policy Dependency Test ("subsidy가 사라져도 고객이 구매할 것인가") and a Cyclicality Test (structural long-term demand vs. short-term earnings volatility), and issues a verdict: PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE. Trigger when asked to check "structural demand", "구조적 수요", "Structural, not cyclical", "정책 의존도", "이 시장이 구조적인지", "why must this market exist", or to screen a company/market against the house's Structural Demand principle. Do not trigger for generic industry-growth or TAM analysis requests that don't ask about structural vs. cyclical demand.
---

# Structural Demand Screening

이 스킬은 하우스 투자 원칙 1번 "Structural, not cyclical"을 평가한다. 이 원칙의 명제는 다음과 같다.

> 정책이나 유행에 의해 일시적으로 만들어진 수요가 아니라, 기업의 경제적 의사결정을 바꾸는 비가역적이고 장기적인 산업 변화에서 발생하는 수요에 투자한다.

핵심 질문은 다음 하나로 요약된다.

> "이 기업의 제품/서비스에 대한 수요가 구조적(structural)인가, 아니면 경기·정책·유행에 의존하는 일시적(cyclical / policy-driven) 수요인가?"

해당 기업이 성장 산업에 속한다는 이유만으로, 또는 "AI", "energy", "critical minerals", "automation" 등의 키워드를 언급한다는 이유만으로 Structural Demand로 판단해서는 안 된다. 반드시 **고객의 실제 경제적 의사결정을 변화시키는 장기적 외부 요인**이 존재하는지, 그리고 그 요인이 실제 구매 행동으로 이어졌는지를 증거로 확인해야 한다.

## 1. 입력

다음과 같은 자료를 입력받을 수 있다: 회사명/회사 설명, 제품·기술 설명, 주요 고객, 고객의 구매 이유, 시장 설명, 산업 자료, 고객 사례, 매출 자료, 계약·PoC 자료, IR deck, investment memo, 기사·리서치 자료, 사용자가 제공한 기타 정보.

**정보가 부족하면 추측해서 판정하지 말고, 해당 항목을 "Insufficient Evidence"로 명시한다.** 회사의 IR deck 주장이나 management 발언만으로 driver를 Confirmed 처리하지 않는다.

## 2. Structural Driver 5종

Structural Demand가 존재한다고 판단하려면, 아래 5개 driver 중 **최소 2개 이상이 실제 증거를 바탕으로 Confirmed**여야 한다. 단순히 산업과 관련 있다는 이유만으로 driver를 인정하지 않는다.

### Driver 1. Resource Constraint
**정의**: 전력, 핵심광물, 물, 노동력, 토지, 생산설비 등 물리적 자원의 부족·제약이 고객에게 경제적 문제를 발생시키고, 그 문제 때문에 해당 제품/서비스를 구매해야 하는가?
**예시**: 전력 부족 → ESS/grid optimization/distributed generation, 핵심광물 부족 → recycling/material substitution, 물 부족 → water efficiency/reuse, 노동력 부족 → robotics/automation.
**판단 질문**: 실제 resource shortage/bottleneck이 존재하는가? 그 부족이 고객의 비용·생산량·lead time·사업확장에 영향을 미치는가? 고객이 이를 해결하기 위해 실제 예산을 쓰고 있는가? 향후 5~10년 이상 지속될 가능성이 있는가?
**인정하지 않는 사례**: "전력 산업에 속한다", "광물 시장이 성장한다", "인력 부족이 사회적 이슈다" 같은 narrative만으로는 불충분 — 문제와 구매 행동 사이의 causal link가 입증되어야 한다.

### Driver 2. Cost Curve Shift
**정의**: subsidy나 일시적 정책 지원을 제외한 unsubsidized economics 기준으로, 기존 방식 대비 새로운 방식의 경제성이 지속적으로 개선되는 구조가 존재하는가? (단위 예: $/kWh, $/kg, $/ton, $/unit, $/MW, $/hour)
**판단 질문**: 핵심 cost metric은 무엇인가? 지난 수년간 cost curve가 개선되어 왔는가? 향후 cost-down mechanism이 명확한가? subsidy 없이도 성립하는가? scale/yield/automation/learning curve/material substitution 등 구체적 개선 요인이 있는가?
**인정하지 않는 사례**: subsidy가 있어야만 기존 기술보다 저렴함, "대량생산하면 저렴해질 것"이라는 주장만 존재, cost-down roadmap에 구체적 물리적/경제적 근거가 없음.

### Driver 3. Infrastructure Replacement Cycle
**정의**: 기존 산업 인프라의 노후화, 용량 부족, 기술 전환 때문에 장기간에 걸친 필수적 capex replacement/expansion cycle이 발생하고 있는가? (예: grid modernization, transmission/distribution infrastructure, factory automation, industrial electrification, data center power infrastructure, battery manufacturing infrastructure)
**판단 질문**: 기존 infrastructure의 평균 수명/교체주기가 존재하는가? 현재 capacity shortage/modernization need가 있는가? 산업 전체에서 장기 CAPEX가 예정되어 있는가? 고객의 투자가 discretionary한가, 필수적인가? 이 CAPEX cycle이 수년 이상 지속될 근거가 있는가?
**인정하지 않는 사례**: 특정 한 해의 CAPEX boom, 일회성 정부 프로젝트, 경기 상승기에만 발생하는 설비투자.

### Driver 4. Supply Chain Reconfiguration
**정의**: 고객이 단순히 최저가격을 추구하는 것을 넘어 공급 안정성, 지정학적 위험, lead time, single-source dependence, 국가별 공급망 concentration 등을 이유로 기존 공급망을 구조적으로 재편하고 있는가? (예: critical minerals, battery materials, semiconductor materials, domestic/regional manufacturing, recycling and circular materials)
**판단 질문**: 기존 supply chain에 실제 concentration risk가 존재하는가? 고객이 dual sourcing/localization/reshoring을 진행하고 있는가? 가격 premium을 지불하면서도 공급 안정성을 선택하는 사례가 있는가? 장기 procurement strategy가 변화하고 있는가? 실제 contract/sourcing decision에 반영되고 있는가?
**인정하지 않는 사례**: 단순한 지정학적 narrative, "미중 갈등 때문에 중요하다" 수준의 설명, 실제 고객 procurement 변화가 확인되지 않는 경우.

### Driver 5. Productivity Imperative
**정의**: 인력, 에너지, 원료, 생산 capacity 등의 제약 때문에 고객이 신기술을 도입하지 않으면 경제적 경쟁력을 유지하기 어려운 상황인가? (예: 인력 부족 → robotics/AI automation, 높은 에너지 비용 → energy efficiency, 원료 비용 상승 → material efficiency, 낮은 생산 yield → manufacturing optimization)
**판단 질문**: 고객이 해결하려는 핵심 productivity bottleneck은 무엇인가? 기술을 도입하지 않을 경우 발생하는 경제적 손실은 무엇인가? 노동시간/에너지/생산량/yield/downtime 등으로 정량화 가능한가? 기술 도입이 nice-to-have가 아니라 increasingly must-have가 되고 있는가?
**인정하지 않는 사례**: 단순 convenience 개선, 고객 ROI가 불분명한 기능 개선, 혁신적이라는 이유만으로 도입 필요성을 주장.

## 3. 판정 절차

**Step 1. Demand Source Identification** — 회사의 매출 또는 향후 수요를 발생시키는 근본 원인을 3~5개 이내로 정리한다.

**Step 2. Driver Mapping** — 각 demand source를 위 5개 driver에 mapping한다.

**Step 3. Evidence Validation** — 각 driver를 다음 세 단계로 분류한다.

| 단계 | 기준 |
|---|---|
| Confirmed | 객관적·구체적 증거가 있어 해당 driver가 실제 고객 구매를 유발하고 있다고 판단됨 |
| Plausible | 논리는 타당하지만 실제 고객 행동/정량 데이터가 아직 부족함 |
| Not Demonstrated | 관련 narrative는 있으나 구조적 수요를 입증할 증거가 없음 |

**Plausible은 통과 요건으로 계산하지 않는다.** Confirmed가 최소 2개 있어야 driver 조건을 통과한다.

항상 다음 causal chain이 실제로 연결되는지 확인하고, 하나라도 끊기면 해당 driver의 확신도를 낮춘다.

```
Structural Change → Customer Economic Problem → Purchasing Decision → Company Revenue
```

## 4. Evidence Standard (우선순위)

가능하면 다음 순서로 evidence의 신뢰도를 높게 평가한다: (1) 실제 고객 구매/repeat order, (2) 고객 계약/purchase order/paid PoC, (3) 고객 CAPEX/procurement decision, (4) 고객 인터뷰 또는 공개 발언, (5) 산업의 실제 가격/공급/capacity 데이터, (6) 장기 산업 CAPEX 계획, (7) 제3자 industry research, (8) 회사 management 주장, (9) 일반적인 market narrative.

**회사의 IR deck 주장이나 management 발언만으로는 driver를 Confirmed 처리하지 않는다.** (1)~(6) 수준의 근거가 있어야 Confirmed로 분류할 수 있고, (7)~(9)만 있는 경우는 최대 Plausible에 그친다.

## 5. Policy Dependency Test

Structural Demand 판단과 별도로 반드시 평가한다.

> "내일부터 주요 subsidy, tax credit 또는 climate-related policy support가 사라져도 고객은 이 제품을 구매할 것인가?"

`Yes / Mostly Yes / Unclear / Mostly No / No` 중 하나로 판정하고 이유를 설명한다. 정책이 시장 형성을 가속할 수는 있지만, 정책 자체가 수요의 유일한 원인이면 Structural Demand로 판단하지 않는다.

## 6. Cyclicality Test

산업 자체가 구조적으로 성장하더라도, 기업 실적은 commodity price, construction cycle, semiconductor cycle 등 단기 경기변동에 노출될 수 있다. **Structural과 Cyclical은 binary opposite이 아니다.** 장기 demand driver(structural)와 단기 실적 변동성(cyclical exposure)을 분리해서 설명한다. (예: 장기적인 전력망 증설 수요는 structural하지만, 단기적으로 utility CAPEX timing에 따라 실적 변동성이 존재할 수 있다.)

## 7. 최종 판정

| 판정 | 조건 |
|---|---|
| **PASS** — Strong Structural Demand | Confirmed driver ≥ 2, 장기 지속성 근거 충분, 정책 의존도 낮거나 제거 가능, causal link 명확 |
| **CONDITIONAL PASS** | Confirmed driver 1개 + 추가 driver가 Plausible, 추가 DD 필요 |
| **FAIL** | Confirmed driver 0~1개, 수요가 주로 subsidy/regulation/commodity cycle/일시적 trend에서 발생, causal link 약함 |
| **INSUFFICIENT EVIDENCE** | 판단에 필요한 정보 자체가 부족 |

## 8. 출력 형식

항상 다음 구조를 그대로 사용한다.

```
## Structural Demand Verdict
Verdict: PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE
One-line Thesis: (이 기업의 수요가 왜 구조적이거나 구조적이지 않은지 한 문장)

## Structural Driver Assessment
| Driver | Status | Evidence | Why it changes customer behavior |
| Resource Constraint | Confirmed/Plausible/Not Demonstrated | … | … |
| Cost Curve Shift | … | … | … |
| Infrastructure Replacement Cycle | … | … | … |
| Supply Chain Reconfiguration | … | … | … |
| Productivity Imperative | … | … | … |

## Confirmed Structural Drivers
(Confirmed된 driver만 근거와 함께 정리)

## Policy Dependency
Rating: Yes / Mostly Yes / Unclear / Mostly No / No
(정책이 사라져도 고객이 구매할 것인가에 대한 설명)

## Cyclical Exposure
(structural demand와 별개로 노출된 단기 cycle 설명)

## Key Evidence
(판단을 지지하는 가장 중요한 증거 3~5개)

## Missing Evidence / DD Questions
(부족한 증거 최대 5개, 경영진/고객에게 실제로 물을 수 있을 정도로 구체적으로. 예: "고객의 구매 결정에서 정부 subsidy가 제거될 경우 IRR은 어떻게 변하는가?", "상위 5개 고객 중 몇 개가 공급망 안정성을 이유로 기존 supplier에서 전환했는가?")

## IC Conclusion
Why must this market exist? (시장 규모가 아니라 구조적·경제적 필연성을 2~3문장으로)
```

## 9. 분석 원칙 (필수 준수)

- **Do not keyword-match.** 산업/기술 키워드 언급만으로 structural이라고 판단하지 않는다.
- **Distinguish problem from solution.** 기술의 우수성이 아니라, 그 기술이 해결하는 underlying problem에 구조적 수요가 있는지를 판단한다.
- **Distinguish market growth from structural demand.** 높은 시장 CAGR은 structural demand의 충분조건이 아니다.
- **Require causality.** Structural Change → Customer Economic Problem → Purchasing Decision → Company Revenue 연결고리를 항상 확인한다.
- **Never fabricate evidence.** 자료에 없는 고객, 계약, 데이터, 시장 수치를 만들어내지 않는다. 근거가 부족하면 반드시 Insufficient Evidence 또는 Plausible로 표시한다.
