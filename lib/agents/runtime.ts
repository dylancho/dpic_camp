/**
 * 원칙 에이전트 공용 런타임.
 *
 * 원칙별 파일에서 각자 `runPrincipleAgent(...)`만 호출하면 된다.
 * 모델 호출 / 스키마 강제 / 재시도 / 프롬프트 뼈대는 여기서 한 번만 처리한다.
 */

import { generateText, Output } from 'ai';
import {
  PrincipleFindingsSchema,
  type AgentInput,
  type PrincipleFindings,
} from '../contract';
import {
  HOUSE_ONE_LINER,
  HOUSE_PHILOSOPHY,
  PRINCIPLE_DEFINITION,
  RUBRIC,
  type PrincipleId,
} from '../philosophy';
import { ARCHETYPES } from '../archetypes';
import { renderEvidence } from '../evidence/pack';

export const MODELS = {
  /** STEP 0 임계치 설정 · 최종 보고서 — 판단 품질이 중요 */
  reasoning: process.env.MODEL_REASONING ?? 'anthropic/claude-opus-5',
  /** 원칙 에이전트 4개 병렬 — 속도/비용 */
  principle: process.env.MODEL_PRINCIPLE ?? 'anthropic/claude-sonnet-5',
} as const;

const BASE_RULES = `
너는 임팩트 전문 VC 하우스의 심사역이다. 하우스의 한 줄 정의:
"${HOUSE_ONE_LINER}"

${HOUSE_PHILOSOPHY}

【절대 규칙】
1. 너는 **점수를 매기지 않는다**. 각 기준의 level(이산 판정)만 낸다. 점수 환산은 시스템이 한다.
2. 모든 판정에는 근거 인용을 붙인다. evidence[].sourceId는 반드시 제공된 <<<id>>> 중 하나여야 하고,
   quote는 원문을 **그대로** 옮긴다(요약·의역 금지, 300자 이내).
3. 근거가 없으면 **추측하지 말고** verdict='unknown', level=0으로 두고 missingData에
   "무엇이 없어서 판단하지 못했는지"를 구체적으로 적는다.
   너의 사전지식(기억)으로 사실을 만들어내는 것은 이 하우스에서 가장 큰 실격 사유다.
4. MOU · LOI · 업무협약 · 전략적 제휴 · 수상 · 정부과제 선정은 **상업 증거가 아니다**.
5. 보도자료의 홍보 문구("세계 최초", "혁신적")는 근거가 아니다. 숫자와 계약만 근거다.
6. 판정은 STEP 0에서 확정된 임계치(아래 Calibration)를 기준으로 한다. 임계치를 임의로 바꾸지 않는다.
`.trim();

function buildUserPrompt(principle: PrincipleId, input: AgentInput, extra?: string) {
  const { company, calibration, evidence } = input;
  const spec = RUBRIC[principle];
  const arch = ARCHETYPES[calibration.primaryArchetype];

  const criteriaBlock = spec.criteria
    .map(
      (c) =>
        `- criterionId: "${c.id}" | ${c.label} (배점 ${c.max})\n  level 판정 기준: ${c.levelGuide}\n  가능한 level: 0 ~ ${c.points.length - 1}`,
    )
    .join('\n');

  return `
# 대상 기업
- 기업명: ${company.name}
- 주관사: ${company.underwriter ?? '(미상)'}

# STEP 0 — 확정된 임계치 (이 기준으로 판정할 것)
- 아키타입: ${arch.name}${calibration.secondaryArchetype ? ` (혼합: ${ARCHETYPES[calibration.secondaryArchetype].name})` : ''}
- 분류 근거: ${calibration.classificationRationale}
- 작동 증명 임계치: ${calibration.thresholds.workingProof}
- 상업 증거 임계치: ${calibration.thresholds.commercialEvidence}
- 핵심 cost 단위: ${calibration.thresholds.costUnit} / impact 단위: ${calibration.thresholds.impactUnit}
- 고객 payback 임계: ${calibration.thresholds.paybackThresholdYears}년
- 해자 인정 등록특허 하한: ${calibration.thresholds.patentCountFloor}건
- 가중 관점: ${calibration.weightingNotes.join(' / ')}

# 네가 담당하는 원칙
${PRINCIPLE_DEFINITION[principle]}

# 반드시 채워야 하는 criteria (criterionId를 정확히 그대로 쓸 것)
${criteriaBlock}

${extra ? `# 이 원칙 전용 추가 지침\n${extra}\n` : ''}
# 확보된 근거 (이 안에 없는 사실은 사용하지 말 것)
${renderEvidence(evidence)}

${evidence.gaps.length ? `# 근거 수집 공백\n- ${evidence.gaps.join('\n- ')}\n` : ''}
# 출력
criteria 배열에는 위에 나열된 criterionId를 **빠짐없이 각각 한 번씩** 포함할 것.
`.trim();
}

export async function runPrincipleAgent(
  principle: PrincipleId,
  input: AgentInput,
  opts?: { extraGuidance?: string; systemAppendix?: string },
): Promise<PrincipleFindings> {
  const { output } = await generateText({
    model: MODELS.principle,
    system: opts?.systemAppendix ? `${BASE_RULES}\n\n${opts.systemAppendix}` : BASE_RULES,
    prompt: buildUserPrompt(principle, input, opts?.extraGuidance),
    output: Output.object({ schema: PrincipleFindingsSchema }),
    temperature: 0.2,
    maxRetries: 2,
  });
  return output;
}
