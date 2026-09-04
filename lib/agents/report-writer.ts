/**
 * 최종 투자보고서 작성 에이전트.
 *
 * 주의: 이 에이전트는 **점수를 다시 계산하지 않는다**. 이미 확정된 점수와 게이트 결과를
 * 받아서 IC가 읽을 문서로 만들 뿐이다. 숫자를 바꾸면 안 된다.
 */

import { streamText } from 'ai';
import type { Calibration, CompanyInput, EvidencePack, FinalVerdict, ScoredPrinciple } from '../contract';
import { HOUSE_ONE_LINER, PRINCIPLE_META } from '../philosophy';
import { scoreTableMarkdown } from '../scoring';
import { MODELS } from './runtime';
import { archetypeName } from './calibrate';

const SYSTEM = `
너는 임팩트 VC 하우스의 심사역이고, 지금 IC(투자심의위원회)에 올릴 투자보고서를 쓴다.
하우스 정의: "${HOUSE_ONE_LINER}"

【규칙】
1. 주어진 점수·게이트 판정을 **절대 바꾸지 않는다**. 재계산·재해석 금지.
2. 근거 없는 문장을 쓰지 않는다. 각 주장 옆에 [sourceId] 형태로 출처를 붙인다.
3. 확인하지 못한 것은 "확인되지 않음"이라고 그대로 쓴다. 좋게 포장하지 않는다.
4. 세일즈 문서가 아니다. 반대 논거(bear case)를 회피하면 실격이다.
5. 문체: 한국어 개조식 + 필요한 곳에만 서술. 형용사보다 숫자.
`.trim();

export function buildReportPrompt(args: {
  company: CompanyInput;
  calibration: Calibration;
  scored: ScoredPrinciple[];
  verdict: FinalVerdict;
  evidence: EvidencePack;
}) {
  const { company, calibration, scored, verdict, evidence } = args;

  const detail = scored
    .map((p) => {
      const meta = PRINCIPLE_META[p.principle];
      return `
### ${meta.key}. ${p.name} — ${p.score}/${p.max}점 ${p.zeroedReason ? `(${p.zeroedReason})` : ''}
요약: ${p.findings.summary}
${p.criteria
  .map(
    (c) =>
      `- ${c.label}: ${c.score}/${c.max} (level ${c.level}, ${c.verdict})\n  근거: ${c.rationale}\n  인용: ${
        c.evidence.map((e) => `[${e.sourceId}] "${e.quote}"`).join(' / ') || '(없음)'
      }`,
  )
  .join('\n')}
- Red flags: ${p.findings.redFlags.join(' / ') || '(없음)'}
- 미확인 데이터: ${p.findings.missingData.join(' / ') || '(없음)'}
- Kill questions: ${p.findings.killQuestions.join(' / ') || '(없음)'}
- confidence: ${p.findings.confidence}
`.trim();
    })
    .join('\n\n');

  return `
# 대상
- 기업명: ${company.name}
- 주관사: ${company.underwriter ?? '(미상)'}

# STEP 0 — 확정 임계치
- 아키타입: ${archetypeName(calibration)}
- 분류 근거: ${calibration.classificationRationale}
- 작동 증명: ${calibration.thresholds.workingProof}
- 상업 증거: ${calibration.thresholds.commercialEvidence}
- cost 단위: ${calibration.thresholds.costUnit} / impact 단위: ${calibration.thresholds.impactUnit}
- payback 임계: ${calibration.thresholds.paybackThresholdYears}년 / 등록특허 하한: ${calibration.thresholds.patentCountFloor}건

# 확정 점수 (변경 금지)
${scoreTableMarkdown(scored, verdict)}

# 게이트 판정 (변경 금지)
- 최종: ${verdict.total}/${verdict.max} — ${verdict.bandLabel}
- Pass 여부: ${verdict.pass ? 'Pass' : 'Not Pass'}
- 하드 게이트: ${verdict.hardGateFailed ? '탈락 (Primary Impact Unit 미정의)' : '통과'}
${verdict.gateNotes.map((n) => `- ${n}`).join('\n') || '- (추가 게이트 이슈 없음)'}

# 원칙별 상세
${detail}

# 근거 수집 공백
${evidence.gaps.map((g) => `- ${g}`).join('\n') || '- (없음)'}

# 작성할 문서 구조 (이 순서 그대로, 마크다운)
## 0. 투자 판단 요약
   한 문단으로 결론. 첫 문장에 "${verdict.bandLabel} (${verdict.total}/100)"을 명시.
   ${verdict.hardGateFailed ? '하드 게이트 탈락 사유를 첫 문단에 반드시 쓴다.' : ''}
## 1. STEP 0 — 임계치 캘리브레이션
   아키타입 분류와 설정 임계치를 표로. (우리 하우스 규칙상 스코어링 상단에 반드시 출력)
## 2. Score Pad
   위 점수 표를 그대로 옮긴다.
## 3. 원칙별 심사 의견 (a → b → c → d 순서)
   원칙마다: 판정 / 결정적 근거 2~3개(인용 포함) / 반대 논거 / 미확인 사항
## 4. Bear Case — 이 투자가 실패한다면 무엇 때문인가
   3가지. 각각 어떤 신호가 관측되면 가설이 확증되는지 함께 적는다.
## 5. IC Kill Questions
   경영진에게 던질 질문 5개. 답변에 따라 판단이 뒤집히는 질문만.
## 6. 다음 단계 실사 체크리스트
   미확인 데이터를 어떤 자료로 어떻게 메울지 (요청할 문서명 수준까지 구체적으로).
## 7. 근거 및 한계
   사용한 출처 목록과 이번 분석의 신뢰 한계.
`.trim();
}

export function streamReport(args: Parameters<typeof buildReportPrompt>[0]) {
  return streamText({
    model: MODELS.reasoning,
    system: SYSTEM,
    prompt: buildReportPrompt(args),
    temperature: 0.4,
  });
}
