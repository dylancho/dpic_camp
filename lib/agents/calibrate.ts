/**
 * STEP 0 — Threshold Calibration.  (오케스트레이터 담당: 나)
 *
 * "스코어링 전 필수 수행". 여기서 임계치를 확정하지 않으면 4명의 에이전트가 각자
 * 다른 잣대로 채점하게 되고, 합산 점수가 의미를 잃는다. 이 단계가 파이프라인의 척추다.
 */

import { generateText, Output } from 'ai';
import { CalibrationSchema, type Calibration, type CompanyInput, type EvidencePack } from '../contract';
import { ARCHETYPES, ARCHETYPE_TABLE_MD } from '../archetypes';
import { renderEvidence } from '../evidence/pack';
import { MODELS } from './runtime';
import { HOUSE_ONE_LINER } from '../philosophy';

const SYSTEM = `
너는 임팩트 VC 하우스의 심사 총괄이다. 하우스 정의: "${HOUSE_ONE_LINER}"

지금은 STEP 0 — Threshold Calibration 단계다. 아직 점수를 매기지 않는다.
대상 기업의 기술·비즈니스 성격을 아키타입 중 하나(또는 혼합)로 분류하고,
각 원칙의 정량 임계치를 그 아키타입 기준으로 **직접 설정**한 뒤 명시하는 것이 전부다.

규칙:
(a) 하드웨어·소재는 가동시간·재현성을 무겁게, SW는 고객 수·retention을 무겁게 본다.
(b) 원천기술은 상업화 타임라인이 길다는 점을 반영해 "실환경 가동 1,000시간" 같은 하드웨어
    기준을 그대로 적용하지 않는다. pilot plant 가동 + 제3자 검증으로 대체한다.
(c) 어떤 아키타입에도 딱 맞지 않으면 가장 가까운 것을 기준으로 조정하고,
    그 판단 근거를 classificationRationale에 **1문장**으로 남긴다.

임계치는 반드시 **검증 가능한 수치·형식**으로 쓴다. ("충분한 검증" 같은 모호한 표현 금지)
`.trim();

export async function calibrateThresholds(
  company: CompanyInput,
  evidence: EvidencePack,
): Promise<Calibration> {
  const { output } = await generateText({
    model: MODELS.reasoning,
    system: SYSTEM,
    prompt: `
# 대상 기업
- 기업명: ${company.name}
- 주관사: ${company.underwriter ?? '(미상)'}

# 아키타입 표
${ARCHETYPE_TABLE_MD}

# 확보된 근거
${renderEvidence(evidence)}

${evidence.gaps.length ? `# 근거 공백\n- ${evidence.gaps.join('\n- ')}\n` : ''}
# 지시
1. primaryArchetype을 정한다. 성격이 겹치면 secondaryArchetype도 채운다(없으면 null).
2. thresholds를 이 기업에 맞게 **수치로** 확정한다.
   - impactUnit은 이 산업에서 실제로 측정되는 물리 단위여야 한다 (tCO2e/ton-제품, kg-회수/ton-투입,
     kWh-절감/yr, m³-절수/yr 등). 이후 c. Physical Impact의 하드 게이트 판정 기준점이 된다.
   - paybackThresholdYears는 아키타입 관행을 따른다 (산업장비 통상 2~3년, 에너지 인프라 5~10년,
     SW는 CAC payback 1~1.5년 환산 등).
   - patentCountFloor는 소재·장비면 3~5건, SW면 1~2건 수준으로 산업 특성에 맞게 정한다.
3. weightingNotes에 "이 기업에서 특히 무겁게 볼 것 / 가볍게 볼 것"을 3~5개 적는다.
   이 문장들은 그대로 4개 원칙 에이전트의 프롬프트에 주입된다.
`.trim(),
    output: Output.object({ schema: CalibrationSchema }),
    temperature: 0.3,
    maxRetries: 2,
  });
  return output;
}

export function archetypeName(c: Calibration) {
  const p = ARCHETYPES[c.primaryArchetype].name;
  return c.secondaryArchetype ? `${p} × ${ARCHETYPES[c.secondaryArchetype].name}` : p;
}
