/**
 * 원칙 a — Structural Demand (시장성, 30점)   ★ 담당: 조원 A
 *
 * 이 파일에서 건드릴 곳은 EXTRA_GUIDANCE 하나뿐이다.
 * 입력/출력 형태(AgentInput → PrincipleFindings)는 lib/contract.ts가 고정하므로
 * 다른 조원 코드와 충돌하지 않는다.
 */

import type { PrincipleAgent } from '../contract';
import { runPrincipleAgent } from './runtime';

const EXTRA_GUIDANCE = `
## driver 판정법 (sd.drivers)
5개 driver 각각에 대해 "이 driver가 **고객의 구매 의사결정을 실제로 바꾸는가**"를 묻는다.
"업계에 그런 트렌드가 있다"는 driver가 아니다. 고객이 그것 때문에 돈을 쓰기 시작해야 driver다.

- resource_constraint: 물리적 부족(전력·핵심광물·물·인력)이 구매를 유발하는가.
  (전력부족→ESS, 광물불안→recycling, 인력부족→robotics)
- cost_curve_shift: unsubsidized 기준 $/kWh·$/kg·$/ton의 지속적 개선 경로가 실제로 존재하는가.
- infrastructure_replacement: grid modernization·factory automation·데이터센터 전력 등
  장기 capex cycle에 물려 있는가.
- supply_chain_reconfiguration: 비용이 아니라 공급안정성·지정학·lead time 때문에 재편이 일어나는가.
- productivity_imperative: 인력·에너지·원료 문제로 신기술 도입이 **불가피**한가 (선택이 아니라).

gateSignals.structuralDrivers 에 확인된 driver만 담는다. level = 그 배열 길이 (3 이상이면 3).
철학상 최소 2개 이상이어야 원칙 충족이므로, 1개 이하면 redFlags에 명시할 것.

## Subsidy Stress Test (sd.subsidy)
"보조금·정책 인센티브를 0으로 두면 이 수요가 남는가"를 직접 계산해본다.
RE100·탄소중립 목표 같은 **선언적 정책**은 수요가 아니다.
매출의 상당 부분이 정부 실증과제·보급사업이면 level 0에 가깝게 본다.
판단할 데이터가 없으면 level 0 + verdict='unknown'. (모르면 통과시키지 않는다 — 우리는
"정책도 유행도 아닌 구조적 수요"에 투자한다)

## bottom-up TAM (sd.tam)
"시장조사기관 기준 2030년 XX조원"은 level 0이다.
(국내 대상 설비 수 × 대당 단가 × 현실적 침투율) 형태로 분해 가능해야 level 2다.
`.trim();

export const structuralDemandAgent: PrincipleAgent = (input) =>
  runPrincipleAgent('structural_demand', input, { extraGuidance: EXTRA_GUIDANCE });
