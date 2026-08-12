/**
 * 결정론적 채점 & Cut-off 엔진.
 *
 * LLM은 여기 들어오지 않는다. 에이전트가 낸 level만 받아서 Score Pad대로 계산하고,
 * 하드 게이트 / 필수조건 / 편중방지 Floor를 순서대로 적용한다.
 * → 같은 findings면 항상 같은 점수가 나온다. IC에서 방어 가능한 유일한 방식.
 */

import {
  CUTOFF,
  PRINCIPLE_META,
  PRINCIPLE_ORDER,
  RUBRIC,
  TOTAL_MAX,
  scoreForLevel,
  type PrincipleId,
} from './philosophy';
import type {
  EvidencePack,
  FinalVerdict,
  PrincipleFindings,
  ScoredCriterion,
  ScoredPrinciple,
} from './contract';

/**
 * 인용 검증: EvidencePack에 실제로 없는 sourceId를 인용했으면 버린다.
 * (환각 인용을 점수 근거로 쓰지 않기 위한 방어)
 */
function sanitizeEvidence(findings: PrincipleFindings, pack: EvidencePack): PrincipleFindings {
  const valid = new Set(pack.items.map((i) => i.id));
  return {
    ...findings,
    criteria: findings.criteria.map((c) => ({
      ...c,
      evidence: c.evidence.filter((e) => valid.has(e.sourceId)),
    })),
  };
}

export function scorePrinciple(
  principle: PrincipleId,
  rawFindings: PrincipleFindings,
  pack: EvidencePack,
): ScoredPrinciple {
  const findings = sanitizeEvidence(rawFindings, pack);
  const spec = RUBRIC[principle];
  const meta = PRINCIPLE_META[principle];

  const criteria: ScoredCriterion[] = spec.criteria.map((cs) => {
    const f = findings.criteria.find((x) => x.criterionId === cs.id);
    const level = f?.level ?? 0;
    return {
      criterionId: cs.id,
      label: cs.label,
      max: cs.max,
      level,
      score: f ? scoreForLevel(cs, level) : 0,
      verdict: f?.verdict ?? 'unknown',
      rationale: f?.rationale ?? '해당 기준에 대한 판정이 반환되지 않아 0점 처리했습니다.',
      evidence: f?.evidence ?? [],
    };
  });

  const rawScore = criteria.reduce((s, c) => s + c.score, 0);
  let score = rawScore;
  let zeroedReason: string | undefined;

  // ── 필수 조건: Proven Scalability (A) ≥1 · (B) ≥2 미충족 시 해당 원칙 0점 처리 ──
  if (principle === 'proven_scalability') {
    const a = findings.gateSignals.provenWorkingCount ?? levelOf(criteria, 'ps.working');
    const b = findings.gateSignals.moatCount ?? levelOf(criteria, 'ps.moat');
    if (a < 1 || b < 2) {
      score = 0;
      zeroedReason =
        `필수 조건 미충족 → 0점 처리 (작동 증명 ${a}/1 이상 필요, 해자 ${b}/2 이상 필요)`;
    }
  }

  const floor = Math.ceil(spec.max * spec.floorRatio);

  return {
    principle,
    name: meta.name,
    category: meta.category,
    max: spec.max,
    rawScore,
    score,
    floor,
    belowFloor: score < floor,
    zeroedReason,
    criteria,
    findings,
  };
}

function levelOf(criteria: ScoredCriterion[], id: string): number {
  return criteria.find((c) => c.criterionId === id)?.level ?? 0;
}

export function applyCutoff(scored: ScoredPrinciple[]): FinalVerdict {
  const total = scored.reduce((s, p) => s + p.score, 0);
  const gateNotes: string[] = [];

  // ── 하드 게이트: Physical Impact의 Primary Impact Unit 미정의 시 총점 무관 탈락 ──
  const pi = scored.find((p) => p.principle === 'physical_impact');
  const unitLevel = pi ? levelOf(pi.criteria, 'pi.unit') : 0;
  const unitDefined = Boolean(pi?.findings.gateSignals.primaryImpactUnit) && unitLevel > 0;
  const hardGateFailed = !unitDefined;
  if (hardGateFailed) {
    gateNotes.push(
      '【하드 게이트 탈락】 Primary Impact Unit이 정의되지 않았습니다. ' +
        '측정 불가능한 임팩트는 서사(narrative)로 간주하므로 총점과 무관하게 탈락 처리합니다.',
    );
  }

  // ── 필수 조건 위반 기록 ──
  for (const p of scored) {
    if (p.zeroedReason) {
      gateNotes.push(`【필수 조건】 ${p.name}: ${p.zeroedReason}`);
    }
  }

  // ── 편중 방지 Floor: 각 원칙 자기 배점의 60% 미만이면 IC 특별승인 대상 ──
  const needsICApproval = scored.filter((p) => p.belowFloor).map((p) => p.principle);
  for (const p of scored.filter((x) => x.belowFloor)) {
    gateNotes.push(
      `【편중 방지 Floor】 ${p.name} ${p.score}/${p.max}점으로 floor(${p.floor}점) 미달 → ` +
        `총점이 70을 넘어도 IC 특별승인 대상입니다.`,
    );
  }

  const bandDef = hardGateFailed
    ? CUTOFF.bands[CUTOFF.bands.length - 1]
    : CUTOFF.bands.find((b) => total >= b.min)!;

  return {
    total,
    max: TOTAL_MAX,
    band: bandDef.band,
    bandLabel: hardGateFailed ? 'Reject (하드 게이트 탈락)' : bandDef.label,
    pass: !hardGateFailed && total >= CUTOFF.passScore && needsICApproval.length === 0,
    hardGateFailed,
    gateNotes,
    needsICApproval,
  };
}

/** 보고서 프롬프트/UI에 넣을 스코어 테이블 마크다운 */
export function scoreTableMarkdown(scored: ScoredPrinciple[], verdict: FinalVerdict): string {
  const rows = PRINCIPLE_ORDER.map((id) => {
    const p = scored.find((x) => x.principle === id)!;
    const sub = p.criteria.map((c) => `${c.label} ${c.score}/${c.max}`).join(' · ');
    return `| ${PRINCIPLE_META[id].key}. ${p.name} | ${p.category} | **${p.score} / ${p.max}** | ${sub} |`;
  });
  return [
    '| 원칙 | 카테고리 | 점수 | 세부 |',
    '|---|---|---|---|',
    ...rows,
    `| **합계** |  | **${verdict.total} / ${verdict.max}** | ${verdict.bandLabel} |`,
  ].join('\n');
}
