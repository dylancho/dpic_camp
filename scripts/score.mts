/**
 * 결정론적 채점 + Cut-off.  LLM이 절대 들어오지 않는 단계다.
 *   npm run score -- "에스오에스랩"
 *
 * 입력: runs/<slug>/findings-*.json  (서브에이전트 4개가 각자 쓴 판정)
 * 출력: runs/<slug>/scorecard.md, verdict.json  (+ 콘솔 요약)
 *
 * 서브에이전트가 점수를 직접 매기지 않고 level만 내는 이유:
 * 같은 근거면 항상 같은 점수가 나와야 IC에서 방어된다.
 */

import { writeFileSync } from 'node:fs';
import { applyCutoff, scorePrinciple, scoreTableMarkdown } from '../lib/scoring';
import { PRINCIPLE_META, PRINCIPLE_ORDER, type PrincipleId } from '../lib/philosophy';
import { readJson, runDir } from '../lib/run-store';
import type { Calibration, EvidencePack, PrincipleFindings, ScoredPrinciple } from '../lib/contract';
import { PrincipleFindingsSchema } from '../lib/contract';
import { ARCHETYPES } from '../lib/archetypes';

const name = process.argv[2];
if (!name) {
  console.error('사용법: npm run score -- "기업명"');
  process.exit(1);
}

const dir = runDir(name);
const evidence = readJson<EvidencePack>(`${dir}/evidence.json`);
if (!evidence) {
  console.error(`${dir}/evidence.json 이 없습니다. 먼저 npm run collect 를 실행하세요.`);
  process.exit(1);
}
const calibration = readJson<Calibration>(`${dir}/calibration.json`);

/** 담당자마다 다른 판정 어휘를 공용 4값으로 정규화한다 */
const VERDICT_SYNONYMS: Record<string, string> = {
  not_met: 'unmet', notmet: 'unmet', 'not demonstrated': 'unmet', fail: 'unmet', no: 'unmet',
  met: 'met', confirmed: 'met', pass: 'met', yes: 'met',
  plausible: 'partial', conditional: 'partial', 'conditional pass': 'partial',
  unverifiable: 'unknown', 'insufficient evidence': 'unknown', 'not disclosed': 'unknown', unclear: 'unknown',
};

function normalizeVerdicts(raw: unknown): unknown {
  const r = raw as { criteria?: { verdict?: unknown }[] };
  for (const c of r?.criteria ?? []) {
    if (typeof c.verdict !== 'string') continue;
    const key = c.verdict.trim().toLowerCase();
    if (['met', 'partial', 'unmet', 'unknown'].includes(key)) {
      c.verdict = key;
    } else if (VERDICT_SYNONYMS[key]) {
      c.verdict = VERDICT_SYNONYMS[key];
    }
  }
  return raw;
}

const scored: ScoredPrinciple[] = [];
const problems: string[] = [];

for (const id of PRINCIPLE_ORDER as PrincipleId[]) {
  const file = `${dir}/findings-${id}.json`;
  const raw = readJson<unknown>(file);
  if (!raw) {
    problems.push(`${file} 없음 → ${PRINCIPLE_META[id].name} 0점 처리 (${PRINCIPLE_META[id].owner} 담당)`);
    scored.push(
      scorePrinciple(
        id,
        {
          criteria: [],
          gateSignals: {},
          redFlags: ['판정 파일이 제출되지 않았습니다.'],
          missingData: ['에이전트 미실행'],
          killQuestions: [],
          confidence: 0,
          summary: '(미제출)',
        },
        evidence,
      ),
    );
    continue;
  }

  // 계약서(Zod) 위반은 여기서 잡는다 — 조원이 형식을 어기면 조용히 넘어가지 않는다.
  // 다만 4명이 서로 다른 판정 어휘를 쓰는 프로젝트라(조원 D는 MET/NOT_MET/UNVERIFIABLE,
  // 조원 A·B 스킬은 Confirmed/Not Demonstrated) 동의어가 새어 들어오는 것은 형식 오류로
  // 취급하지 않고 정규화한다. 진짜 못 알아볼 값만 오류로 보고한다.
  const parsed = PrincipleFindingsSchema.safeParse(normalizeVerdicts(raw));
  if (!parsed.success) {
    problems.push(
      `${file} 형식 오류 → ${parsed.error.issues.slice(0, 3).map((i) => `${i.path.join('.')}: ${i.message}`).join(' / ')}`,
    );
  }
  const findings = (parsed.success ? parsed.data : raw) as PrincipleFindings;

  // 에이전트가 새로 찾은 근거를 채점 전에 근거 풀에 편입한다.
  // 이걸 빼먹으면 그 인용들이 전부 "없는 sourceId"로 간주돼 버려진다.
  for (const item of findings.extraEvidence ?? []) {
    if (!evidence.items.some((x) => x.id === item.id)) evidence.items.push(item);
  }

  scored.push(scorePrinciple(id, findings, evidence));
}

// 편입된 근거를 파일에도 반영해 다음 실행·보고서에서 인용이 유지되게 한다
writeFileSync(`${dir}/evidence.json`, JSON.stringify(evidence, null, 2), 'utf8');

const verdict = applyCutoff(scored);

/* ── 콘솔 요약 ─────────────────────────────────────────── */
console.log('');
for (const p of scored) {
  const bar = '█'.repeat(Math.round((p.score / p.max) * 20)).padEnd(20, '·');
  const flag = p.zeroedReason ? ' ⛔' : p.belowFloor ? ' ⚠ floor 미달' : '';
  console.log(
    `  ${PRINCIPLE_META[p.principle].key}. ${p.name.padEnd(20)} ${bar} ${String(p.score).padStart(2)}/${p.max}${flag}`,
  );
}
console.log(`\n  총점 ${verdict.total}/${verdict.max} — ${verdict.bandLabel}`);
console.log(`  Pass: ${verdict.pass ? 'YES' : 'NO'}${verdict.hardGateFailed ? ' (하드 게이트 탈락)' : ''}`);
for (const n of verdict.gateNotes) console.log(`    • ${n}`);
if (problems.length) {
  console.log('\n  제출 문제:');
  for (const p of problems) console.log(`    ✗ ${p}`);
}

/* ── scorecard.md ──────────────────────────────────────── */
const md = [
  `# ${name} · Score Pad`,
  '',
  calibration
    ? [
        '## STEP 0 — 확정 임계치',
        '',
        `- 아키타입: **${ARCHETYPES[calibration.primaryArchetype].name}**${
          calibration.secondaryArchetype ? ` × ${ARCHETYPES[calibration.secondaryArchetype].name}` : ''
        }`,
        `- 분류 근거: ${calibration.classificationRationale}`,
        `- 작동 증명: ${calibration.thresholds.workingProof}`,
        `- 상업 증거: ${calibration.thresholds.commercialEvidence}`,
        `- cost 단위: ${calibration.thresholds.costUnit} / impact 단위: ${calibration.thresholds.impactUnit}`,
        `- payback 임계: ${calibration.thresholds.paybackThresholdYears}년 / 등록특허 하한: ${calibration.thresholds.patentCountFloor}건`,
        '',
      ].join('\n')
    : '> ⚠ calibration.json 이 없습니다. STEP 0을 건너뛴 채점은 아키타입 보정이 반영되지 않습니다.\n',
  '## 점수',
  '',
  scoreTableMarkdown(scored, verdict),
  '',
  '## 게이트 판정',
  '',
  `- 최종: **${verdict.total}/${verdict.max}** — ${verdict.bandLabel}`,
  `- Pass: ${verdict.pass ? 'YES' : 'NO'}`,
  `- 하드 게이트: ${verdict.hardGateFailed ? '**탈락** (Primary Impact Unit 미정의)' : '통과'}`,
  ...verdict.gateNotes.map((n) => `- ${n}`),
  '',
  '## 원칙별 상세',
  '',
  ...scored.flatMap((p) => [
    `### ${PRINCIPLE_META[p.principle].key}. ${p.name} — ${p.score}/${p.max}`,
    '',
    p.zeroedReason ? `> ⛔ ${p.zeroedReason}\n` : '',
    p.findings.summary,
    '',
    ...p.criteria.map(
      (c) =>
        `- **${c.label}** ${c.score}/${c.max} (level ${c.level}, ${c.verdict})\n  - ${c.rationale}\n` +
        (c.evidence.length
          ? c.evidence.map((e) => `  - 인용 \`[${e.sourceId}]\` "${e.quote}"`).join('\n')
          : '  - 인용 없음'),
    ),
    '',
    p.findings.redFlags.length ? `**Red flags**\n${p.findings.redFlags.map((r) => `- ${r}`).join('\n')}\n` : '',
    p.findings.missingData.length
      ? `**미확인 데이터**\n${p.findings.missingData.map((r) => `- ${r}`).join('\n')}\n`
      : '',
    p.findings.killQuestions.length
      ? `**Kill questions**\n${p.findings.killQuestions.map((r) => `- ${r}`).join('\n')}\n`
      : '',
    // 담당 조원 스킬의 서술 전문 — 보고서 작성 에이전트가 이 부분을 그대로 인용한다
    p.findings.skillReport ? `<details><summary>담당 스킬 상세 리포트</summary>\n\n${p.findings.skillReport}\n\n</details>\n` : '',
  ]),
  evidence.gaps.length ? `## 근거 수집 공백\n\n${evidence.gaps.map((g) => `- ${g}`).join('\n')}\n` : '',
  problems.length ? `## 제출 문제\n\n${problems.map((p) => `- ${p}`).join('\n')}\n` : '',
].join('\n');

writeFileSync(`${dir}/scorecard.md`, md, 'utf8');
writeFileSync(`${dir}/verdict.json`, JSON.stringify({ verdict, scored }, null, 2), 'utf8');
console.log(`\n  → ${dir}/scorecard.md`);
