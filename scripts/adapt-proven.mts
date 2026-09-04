/**
 * 원칙 d의 Proven Scalability 파이썬 에이전트 → 공용 채점 형식 어댑터.
 *   npm run adapt:d -- "<기업명>" [증거파일.json]
 *
 * 왜 어댑터인가:
 *   D의 에이전트는 자체 결정론 채점기(A 12 · B 8 · C 5 = 25점)를 갖고 있고, 그 배점이
 *   우리 Score Pad의 Proven Scalability 25점과 정확히 같다. 그래서 그의 채점기를
 *   버리지 않고 **판정 결과(resolved_statuses)를 우리 level로 옮기기만** 한다.
 *   - A1~A3 중 MET 개수 → ps.working  (0~3)
 *   - B1~B4 중 MET 개수 → ps.moat     (0~4)
 *   - C1~C3 중 MET 개수 → ps.scaleup  (0~2로 clamp)
 *
 * 인용도 살린다: D가 수집한 근거를 evidence.json에 `psa-*` id로 편입해야
 * 우리 채점기의 환각 인용 필터(sanitizeEvidence)를 통과한다.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, writeFileSync } from 'node:fs';
import { config } from 'dotenv';
import { readJson, runDir } from '../lib/run-store';
import type { Calibration, EvidenceItem, PrincipleFindings } from '../lib/contract';

config({ path: '.env.local', quiet: true });

type DStatus = 'MET' | 'NOT_MET' | 'UNVERIFIABLE';
type DEvidence = {
  criterion_id: string;
  status: DStatus;
  source_tier: number;
  source_url: string | null;
  quote: string;
  extracted_value: string | null;
};
type DResult = {
  verdict: string;
  score: number;
  block_scores: { a: number; b: number; c: number };
  gate_failed: string[];
  evidence_coverage: number;
  calibration: { archetype: string; note: string | null };
  evidence: DEvidence[];
  resolved_statuses: Record<string, DStatus>;
  met_tier_profile: Record<string, number>;
  research_notes: string[];
  diligence_questions: string[];
};

const name = process.argv[2];
if (!name) {
  console.error('사용법: npm run adapt:d -- "기업명" [증거파일.json]');
  process.exit(1);
}
const evidenceArg = process.argv[3];
const dir = runDir(name);

// 아키타입은 STEP 0-B 결과를 그대로 물려준다 (D의 에이전트는 스스로 분류하지 않는다)
const calibration = readJson<Calibration>(`${dir}/calibration.json`);
const archetype = calibration?.primaryArchetype;

const args = ['-m', 'agents.proven_scalability', '--company', name, '--json'];
if (archetype) args.push('--archetype', archetype);
const evidencePath = evidenceArg ?? `${dir}/evidence-proven-scalability.json`;
if (existsSync(evidencePath)) args.push('--evidence', evidencePath);
else {
  console.warn(
    `⚠ ${evidencePath} 없음 — DART 규칙 추출만으로 채점합니다.\n` +
      `  (서브에이전트 principle-d 가 docs/agent-instructions/ 를 따라 이 파일을 먼저 만들어야 합니다)`,
  );
}

const py = spawnSync('python', args, { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
if (py.error || py.status !== 0) {
  console.error('원칙 d 에이전트 실행 실패:', py.stderr || py.error?.message);
  console.error('  → pip install -e ".[dev]" 를 먼저 실행했는지 확인하세요.');
  process.exit(1);
}

const result = JSON.parse(py.stdout) as DResult;

/* ── resolved_statuses → level ─────────────────────────── */
const countMet = (prefix: string) =>
  Object.entries(result.resolved_statuses).filter(
    ([id, st]) => id.startsWith(prefix) && st === 'MET',
  ).length;

const aCount = countMet('A');
const bCount = countMet('B');
const cCount = countMet('C');

const verdictOf = (n: number, statuses: DStatus[]): PrincipleFindings['criteria'][number]['verdict'] => {
  if (n > 0) return 'met';
  if (statuses.every((s) => s === 'UNVERIFIABLE')) return 'unknown';
  return 'unmet';
};
const statusesOf = (prefix: string) =>
  Object.entries(result.resolved_statuses)
    .filter(([id]) => id.startsWith(prefix))
    .map(([, st]) => st);

/* ── D의 근거를 evidence.json 에 편입 (인용 유효화) ────── */
const pack = readJson<{ items: EvidenceItem[]; [k: string]: unknown }>(`${dir}/evidence.json`);
const newItems: EvidenceItem[] = result.evidence.map((e, i) => ({
  id: `psa-${i + 1}`,
  source: 'web' as const,
  title: `[원칙 d] ${e.criterion_id} (${e.status}, ${e.source_tier}급 근거)`,
  url: e.source_url ?? undefined,
  content: e.extracted_value ? `${e.quote}\n[정량값] ${e.extracted_value}` : e.quote,
}));
if (pack) {
  const existing = new Set(pack.items.map((i) => i.id));
  pack.items.push(...newItems.filter((i) => !existing.has(i.id)));
  writeFileSync(`${dir}/evidence.json`, JSON.stringify(pack, null, 2), 'utf8');
}

const citationsFor = (prefix: string) =>
  result.evidence
    .map((e, i) => ({ e, id: `psa-${i + 1}` }))
    .filter(({ e }) => e.criterion_id.startsWith(prefix))
    .slice(0, 3)
    .map(({ e, id }) => ({ sourceId: id, quote: e.quote.slice(0, 300) }));

const detail = (prefix: string) =>
  Object.entries(result.resolved_statuses)
    .filter(([id]) => id.startsWith(prefix))
    .map(([id, st]) => `${id}=${st}`)
    .join(', ');

/* ── 두 채점기가 갈리는 지점을 명시적으로 드러낸다 ──────────
 *
 * 원칙 d의 scoring.py 는 필수 조건 미충족 시 **그 블록만** 0으로 두고 나머지 블록 점수를
 * 살린다 (예: A 0건·B 3건·C 2건 → 0+7+4 = 11/25).
 * 우리 하우스 헌법은 다르다:
 *   "필수 조건 — Proven Scalability의 (A) 1개 이상·(B) 2개 이상 미충족 시 해당 원칙 0점 처리"
 * '해당 원칙'은 a/b/c/d 중 하나를 가리킨다. (A)·(B)는 원칙이 아니라 조건이다.
 * 따라서 최종 점수는 lib/scoring.ts 가 25점 전체를 0으로 만드는 쪽이 문서대로다.
 *
 * D의 블록 점수는 버리지 않는다 — "어느 블록이 얼마나 강했는가"는 실사에서 쓸모 있는 진단이다.
 * 다만 두 숫자가 갈릴 때 조용히 넘어가면 "내 CLI는 11점인데 보고서는 0점"이라는 혼선이 난다.
 * 그래서 갈리는 순간 summary와 redFlags에 그 사실을 박아 넣는다.
 */
const houseGateFails = aCount < 1 || bCount < 2;
const divergence = houseGateFails && result.score > 0;
const divergenceNote =
  `원칙 d 채점기는 실패 블록만 0으로 두어 ${result.score}/25 를 산출했으나, ` +
  `하우스 Cut-off 규칙("(A)≥1·(B)≥2 미충족 시 해당 원칙 0점 처리")에 따라 최종 점수는 0/25로 처리된다. ` +
  `블록 점수(A ${result.block_scores.a} · B ${result.block_scores.b} · C ${result.block_scores.c})는 ` +
  `어느 축이 강했는지를 보여주는 진단 정보로만 읽을 것.`;

const findings: PrincipleFindings = {
  criteria: [
    {
      criterionId: 'ps.working',
      level: Math.min(3, aCount),
      verdict: verdictOf(aCount, statusesOf('A')),
      rationale:
        `원칙 d의 결정론 채점기 판정: ${detail('A')}. MET ${aCount}건. ` +
        `아키타입 ${result.calibration.archetype} 기준으로 임계치를 적용했다.` +
        (result.calibration.note ? ` 주의: ${result.calibration.note}` : ''),
      evidence: citationsFor('A'),
    },
    {
      criterionId: 'ps.moat',
      level: Math.min(4, bCount),
      verdict: verdictOf(bCount, statusesOf('B')),
      rationale: `원칙 d의 결정론 채점기 판정: ${detail('B')}. MET ${bCount}건 (2건 이상이어야 필수 조건 충족).`,
      evidence: citationsFor('B'),
    },
    {
      criterionId: 'ps.scaleup',
      level: Math.min(2, cCount),
      verdict: verdictOf(cCount, statusesOf('C')),
      rationale: `원칙 d의 결정론 채점기 판정: ${detail('C')}. MET ${cCount}건.`,
      evidence: citationsFor('C'),
    },
  ],
  gateSignals: { provenWorkingCount: aCount, moatCount: bCount },
  redFlags: [
    ...result.research_notes.map((n) => `[조사 결함] ${n}`),
    ...(result.gate_failed.length ? [`D 자체 게이트 미충족 블록: ${result.gate_failed.join(', ')}`] : []),
    ...(divergence ? [`[채점 기준 차이] ${divergenceNote}`] : []),
  ],
  missingData: Object.entries(result.resolved_statuses)
    .filter(([, st]) => st === 'UNVERIFIABLE')
    .map(([id]) => `${id} — 근거를 확인하지 못했다`),
  killQuestions: result.diligence_questions,
  confidence: result.evidence_coverage,
  summary:
    `원칙 d 파이썬 에이전트 판정: ${result.verdict}, 자체 점수 ${result.score}/25 ` +
    `(A ${result.block_scores.a}/12 · B ${result.block_scores.b}/8 · C ${result.block_scores.c}/5). ` +
    `근거 커버리지 ${Math.round(result.evidence_coverage * 100)}%.` +
    (divergence ? ` ⚠ ${divergenceNote}` : ''),
};

writeFileSync(`${dir}/findings-proven_scalability.json`, JSON.stringify(findings, null, 2), 'utf8');
writeFileSync(`${dir}/proven-scalability-raw.json`, JSON.stringify(result, null, 2), 'utf8');

console.log(`\n원칙 d 에이전트 → 공용 형식 변환 완료`);
console.log(`  D 자체 판정 : ${result.verdict} ${result.score}/25`);
console.log(`  변환된 level: ps.working=${Math.min(3, aCount)} ps.moat=${Math.min(4, bCount)} ps.scaleup=${Math.min(2, cCount)}`);
console.log(`  커버리지    : ${Math.round(result.evidence_coverage * 100)}%`);
console.log(`  → ${dir}/findings-proven_scalability.json`);
if (result.research_notes.length) {
  console.log('\n  조사 결함 (커버리지를 그대로 읽지 말 것):');
  for (const n of result.research_notes) console.log(`    ! ${n}`);
}
