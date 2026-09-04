/**
 * 원칙 c — Physical Impact (임팩트성, 20점)   ★ 담당: 나
 *
 * "임팩트는 이야기가 아니라, 측정 가능하고 산업 규모로 확장되는 물리량이어야 한다."
 *
 * 이 원칙만 **하드 게이트**를 갖는다. Primary Impact Unit이 정의되지 않으면 총점이 몇 점이든 탈락.
 * 그래서 다른 세 원칙과 달리 2단계로 돌린다:
 *
 *   STEP c-1. Impact Unit Extraction — 물리 단위를 먼저 확정(또는 확정 불가 선언)한다.
 *   STEP c-2. Scoring — 확정된 단위를 기준선 삼아 4개 기준과 매출 연동을 판정한다.
 *
 * 단계를 나눈 이유: 한 번에 물으면 모델이 "탄소를 줄입니다" 같은 서사를 단위로 착각해서
 * 하드 게이트를 통과시켜 버린다. 게이트 판정은 독립된 호출로 분리해야 방어된다.
 */

import { generateText, Output } from 'ai';
import { z } from 'zod';
import type { AgentInput, PrincipleAgent, PrincipleFindings } from '../contract';
import { renderEvidence } from '../evidence/pack';
import { MODELS, runPrincipleAgent } from './runtime';

/* ------------------------------------------------------------------ *
 * STEP c-1 — Primary Impact Unit 추출
 * ------------------------------------------------------------------ */

const ImpactUnitSchema = z.object({
  /** 측정 가능한 단일 물리 단위. 정의 불가하면 null. */
  unit: z.string().nullable(),
  /** 산정 경계 — 무엇 대비, 어느 범위(cradle-to-gate 등) */
  boundary: z.string().nullable(),
  /** 산정식 — 예: (기존 공정 배출량 - 당사 공정 배출량) / 제품 ton */
  formula: z.string().nullable(),
  /** 비교 기준이 되는 기존 방식(baseline)의 이름 */
  baselineName: z.string().nullable(),
  /** 근거에서 확인된 정량 수치 (없으면 빈 배열) */
  quantities: z.array(z.object({ value: z.string(), sourceId: z.string() })),
  /** 단위가 정의되었다고 볼 수 있는가 */
  isDefined: z.boolean(),
  /** 0=미정의(하드게이트 탈락) 1=단위는 있으나 경계·산정식 모호 2=단위+경계+산정식 명확 */
  level: z.number().int().min(0).max(2),
  reasoning: z.string(),
});
export type ImpactUnit = z.infer<typeof ImpactUnitSchema>;

const UNIT_SYSTEM = `
너는 임팩트 VC의 임팩트 측정 담당이다. 지금 하는 일은 딱 하나:
이 기업의 **Primary Impact Unit**이 실제로 정의 가능한지 판정하는 것.

Primary Impact Unit이란: 제품/서비스 1단위가 만들어내는 사회적 효과를 나타내는
**단일하고 측정 가능한 물리 단위**. 예시:
  tCO2e / ton-제품        (공정 배출 저감)
  kg-회수금속 / ton-투입폐기물  (자원 회수)
  kWh-절감 / 설비-yr      (에너지 효율)
  m³-절수 / yr            (수자원)
  ppm-저감 · kg-폐기물 저감 / 배치

★ 다음은 Primary Impact Unit이 **아니다**. 이런 것만 있으면 isDefined=false, level=0이다:
  - "탄소중립에 기여합니다", "친환경 소재입니다", "ESG 가치를 창출합니다"  → 서사
  - "온실가스를 줄입니다" (얼마나? 무엇 대비?)                            → 방향만 있고 크기 없음
  - 매출액, 고용 인원, 투자 유치액                                        → 기업 성과이지 임팩트가 아님
  - 회사가 구매한 탄소 크레딧, 기부금, CSR 활동                            → 제품과 무관한 상쇄 활동
  - 수상 이력, 인증 획득 자체                                             → 라벨이지 물리량이 아님

경계(boundary)와 산정식(formula)이 없으면 level은 최대 1이다.
근거에 없는 수치를 만들어내지 마라. quantities는 인용 가능한 것만 담는다.
`.trim();

async function extractImpactUnit(input: AgentInput): Promise<ImpactUnit> {
  const { output } = await generateText({
    model: MODELS.reasoning,
    system: UNIT_SYSTEM,
    prompt: `
# 대상 기업
${input.company.name}

# STEP 0에서 이 아키타입에 대해 정한 impact 단위 후보
${input.calibration.thresholds.impactUnit}
(이 후보를 그대로 받아쓰지 말 것. 근거에서 실제로 뒷받침되는지 검증하고, 다르면 바로잡는다.)

# 확보된 근거
${renderEvidence(input.evidence)}

# 지시
이 기업의 Primary Impact Unit을 확정하라. 근거가 서사뿐이면 isDefined=false로 선언하라.
그렇게 선언하면 이 기업은 총점과 무관하게 탈락한다 — 그것이 우리 하우스의 규칙이므로
근거가 부족할 때 통과시키는 것보다 탈락시키는 쪽이 옳다.
`.trim(),
    output: Output.object({ schema: ImpactUnitSchema }),
    temperature: 0.1,
    maxRetries: 2,
  });
  return output;
}

/* ------------------------------------------------------------------ *
 * STEP c-2 — 확정된 단위를 기준으로 스코어링
 * ------------------------------------------------------------------ */

function guidance(unit: ImpactUnit) {
  return `
## STEP c-1에서 확정된 Primary Impact Unit (이 결과를 뒤집지 말 것)
- 단위: ${unit.unit ?? '(정의 불가)'}
- 산정 경계: ${unit.boundary ?? '(없음)'}
- 산정식: ${unit.formula ?? '(없음)'}
- baseline: ${unit.baselineName ?? '(특정되지 않음)'}
- 확인된 수치: ${unit.quantities.length ? unit.quantities.map((q) => `${q.value} [${q.sourceId}]`).join(', ') : '(없음)'}
- 판정: isDefined=${unit.isDefined}, level=${unit.level}
- 근거: ${unit.reasoning}

→ criterionId "pi.unit"의 level은 위 level(${unit.level})을 **그대로** 사용한다.
→ gateSignals.primaryImpactUnit 에는 ${unit.isDefined ? `"${unit.unit}"` : 'null'} 을 넣는다.

## pi.criteria4 — 4개 기준 충족 개수 (level = 충족 개수 0~4)
1. **저감 메커니즘의 진술 가능성**: 공정의 *어떤 배출*이 왜 줄어드는지가 인과로 설명되는가.
   "친환경 공정이라서"는 메커니즘이 아니다. "고온 소성 단계를 상온 전해로 대체해 연료 연소
   배출이 제거된다" 수준이어야 충족이다.
2. **대체 대상의 특정**: 고객 공정에서 대체되는 기존 설비/원료가 **이름으로** 지목되는가.
   (예: "기존 로터리 킬른", "코크스", "황산 침출 공정"). "기존 방식" 같은 총칭은 불충족.
3. **저감 규모 파악 가능**: 총 배출량 대비 % 또는 명확한 물리량으로 표현되는가.
4. **baseline 대비 정량 비교**: 동일 기능의 기존 방식 대비 단위당 저감 효율이 높거나 비용이
   낮다는 점이 **숫자로** 제시되는가.
   ★ 이 4번이 가장 중요하다. 기존 대안보다 못하면 물리적 임팩트가 있어도 시장에서 채택되지
     않는다. baseline 비교가 없으면 나머지 3개를 충족해도 redFlags에 반드시 기록한다.

## pi.linkage — 임팩트–매출 연동 (Revenue↑ = Impact↑)
level 2: 제품 1단위 판매 = 임팩트 N단위. 구조적으로 직결되어 회사가 성장할수록 임팩트가 커진다.
level 1: 연동되지만 비선형이거나 일부 제품군에만 해당.
level 0: 임팩트가 매출과 분리되어 있다 (CSR, 크레딧 구매, 별도 사회공헌 사업).
        → 이 경우 "임팩트를 위해 돈을 쓰는 구조"이므로 우리 철학과 정반대임을 redFlags에 적는다.

## 주의
임팩트 크기가 크다는 이유로 후하게 주지 않는다. 우리는 임팩트에 투자하지만
**임팩트라는 이유로 투자하지 않는다**. 측정 가능성과 baseline 우위가 판정의 전부다.
`.trim();
}

export const physicalImpactAgent: PrincipleAgent = async (input): Promise<PrincipleFindings> => {
  // STEP c-1 — 하드 게이트 판정은 독립 호출로 분리
  const unit = await extractImpactUnit(input);

  // STEP c-2 — 확정된 단위를 기준선으로 스코어링
  const findings = await runPrincipleAgent('physical_impact', input, {
    extraGuidance: guidance(unit),
  });

  // 코드로 한 번 더 강제: STEP c-1의 게이트 판정이 STEP c-2에서 뒤집히지 않게 고정한다.
  const criteria = findings.criteria.map((c) =>
    c.criterionId === 'pi.unit' ? { ...c, level: unit.level } : c,
  );

  return {
    ...findings,
    criteria,
    gateSignals: {
      ...findings.gateSignals,
      primaryImpactUnit: unit.isDefined ? unit.unit : null,
    },
    missingData: unit.isDefined
      ? findings.missingData
      : [
          `Primary Impact Unit 미정의 — ${unit.reasoning}`,
          ...findings.missingData,
        ],
  };
};

/** UI/보고서에서 별도로 보여주기 위해 export */
export { extractImpactUnit };
