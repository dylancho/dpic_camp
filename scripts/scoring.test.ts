/**
 * 채점·게이트 엔진 스모크 테스트 (LLM 호출 없음).
 *   npx tsx scripts/scoring.test.ts
 *
 * 철학의 Cut-off 규칙이 실제로 코드에서 강제되는지 확인한다.
 */

import assert from 'node:assert/strict';
import { applyCutoff, scorePrinciple } from '../lib/scoring';
import type { EvidencePack, PrincipleFindings } from '../lib/contract';
import { PRINCIPLE_ORDER, TOTAL_MAX, type PrincipleId } from '../lib/philosophy';

const pack: EvidencePack = {
  company: { name: '테스트' },
  items: [{ id: 'note-1', source: 'user_note', title: 'n', content: 'c' }],
  gaps: [],
};

function findings(
  levels: Record<string, number>,
  gate: PrincipleFindings['gateSignals'] = {},
): PrincipleFindings {
  return {
    criteria: Object.entries(levels).map(([criterionId, level]) => ({
      criterionId,
      level,
      verdict: 'met' as const,
      rationale: 'r',
      evidence: [{ sourceId: 'note-1', quote: 'q' }],
    })),
    gateSignals: gate,
    redFlags: [],
    missingData: [],
    killQuestions: [],
    confidence: 0.8,
    summary: 's',
  };
}

/** 모든 원칙 만점 세트 */
function perfect() {
  return [
    scorePrinciple(
      'structural_demand',
      findings({ 'sd.drivers': 3, 'sd.subsidy': 2, 'sd.tam': 2 }, {
        structuralDrivers: ['resource_constraint', 'cost_curve_shift', 'productivity_imperative'],
      }),
      pack,
    ),
    scorePrinciple(
      'economic_value',
      findings({ 'ev.tier': 4, 'ev.roi': 2, 'ev.wtp': 2 }, { paidEvidenceCount: 3 }),
      pack,
    ),
    scorePrinciple(
      'physical_impact',
      findings({ 'pi.unit': 2, 'pi.criteria4': 4, 'pi.linkage': 2 }, {
        primaryImpactUnit: 'tCO2e/ton-제품',
      }),
      pack,
    ),
    scorePrinciple(
      'proven_scalability',
      findings({ 'ps.working': 3, 'ps.moat': 4, 'ps.scaleup': 2 }, {
        provenWorkingCount: 3,
        moatCount: 4,
      }),
      pack,
    ),
  ];
}

let failed = 0;
function test(name: string, fn: () => void) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
  } catch (e) {
    failed++;
    console.log(`  ✗ ${name}\n      ${(e as Error).message}`);
  }
}

console.log('\nScore Pad');

test('만점 세트는 정확히 100점이다 (배점 합 = 30+25+20+25)', () => {
  const v = applyCutoff(perfect());
  assert.equal(TOTAL_MAX, 100);
  assert.equal(v.total, 100);
  assert.equal(v.band, 'high_conviction');
  assert.equal(v.pass, true);
});

test('driver 개수 0/1/2/3 → 0/8/13/16점', () => {
  const expected = [0, 8, 13, 16];
  expected.forEach((exp, level) => {
    const s = scorePrinciple('structural_demand', findings({ 'sd.drivers': level }), pack);
    assert.equal(s.criteria.find((c) => c.criterionId === 'sd.drivers')!.score, exp);
  });
});

test('Physical Impact 4개 기준: 2개 이상이면 만점(7)', () => {
  const at = (lv: number) =>
    scorePrinciple('physical_impact', findings({ 'pi.criteria4': lv }), pack).criteria.find(
      (c) => c.criterionId === 'pi.criteria4',
    )!.score;
  assert.equal(at(0), 0);
  assert.equal(at(1), 3);
  assert.equal(at(2), 7);
  assert.equal(at(4), 7);
});

console.log('\nCut-off 규칙');

test('하드 게이트: Primary Impact Unit 미정의 → 총점 무관 탈락', () => {
  const s = perfect().map((p) =>
    p.principle === 'physical_impact'
      ? scorePrinciple(
          'physical_impact',
          findings({ 'pi.unit': 0, 'pi.criteria4': 4, 'pi.linkage': 2 }, { primaryImpactUnit: null }),
          pack,
        )
      : p,
  );
  const v = applyCutoff(s);
  assert.equal(v.hardGateFailed, true);
  assert.equal(v.band, 'reject', '하드게이트 탈락은 총점과 무관하게 reject여야 한다');
  assert.equal(v.pass, false);
  assert.ok(v.gateNotes.some((n) => n.includes('하드 게이트')));
});

test('필수 조건: Proven Scalability (A)<1 또는 (B)<2 → 해당 원칙 0점', () => {
  const noA = scorePrinciple(
    'proven_scalability',
    findings({ 'ps.working': 0, 'ps.moat': 4, 'ps.scaleup': 2 }, { provenWorkingCount: 0, moatCount: 4 }),
    pack,
  );
  assert.equal(noA.rawScore, 13, '원점수는 계산되어야 한다');
  assert.equal(noA.score, 0, '게이트 적용 후 0점이어야 한다');

  const weakB = scorePrinciple(
    'proven_scalability',
    findings({ 'ps.working': 3, 'ps.moat': 1, 'ps.scaleup': 2 }, { provenWorkingCount: 3, moatCount: 1 }),
    pack,
  );
  assert.equal(weakB.score, 0);
  assert.ok(weakB.zeroedReason);
});

test('편중 방지 Floor: 한 원칙이 60% 미만이면 총점 70+ 여도 pass=false', () => {
  const s = perfect().map((p) =>
    p.principle === 'economic_value'
      ? scorePrinciple(
          'economic_value',
          findings({ 'ev.tier': 1, 'ev.roi': 0, 'ev.wtp': 0 }, { paidEvidenceCount: 0 }),
          pack,
        )
      : p,
  );
  const v = applyCutoff(s);
  assert.ok(v.total >= 70, `총점은 70 이상이어야 함 (실제 ${v.total})`);
  assert.equal(v.pass, false, 'floor 미달이면 pass가 아니어야 한다');
  assert.deepEqual(v.needsICApproval, ['economic_value']);
});

test('판정 구간: 60~69 Watchlist / 70~84 Standard IC / 85+ fast-track', () => {
  const band = (evTier: number, psMoat: number) => {
    const s = perfect().map((p) => {
      if (p.principle === 'economic_value')
        return scorePrinciple(
          'economic_value',
          findings({ 'ev.tier': evTier, 'ev.roi': 1, 'ev.wtp': 1 }, {}),
          pack,
        );
      if (p.principle === 'proven_scalability')
        return scorePrinciple(
          'proven_scalability',
          findings({ 'ps.working': 1, 'ps.moat': psMoat, 'ps.scaleup': 1 }, {
            provenWorkingCount: 1,
            moatCount: psMoat,
          }),
          pack,
        );
      return p;
    });
    const v = applyCutoff(s);
    return [v.total, v.band] as const;
  };
  const [t1, b1] = band(4, 4); // 30 + (13+4+2=19) + 20 + (8+8+2=18) = 87
  assert.equal(t1, 87);
  assert.equal(b1, 'high_conviction');

  const [t2, b2] = band(2, 2); // 30 + (6+4+2=12) + 20 + (8+5+2=15) = 77
  assert.equal(t2, 77);
  assert.equal(b2, 'standard_ic');

  const [t3, b3] = band(0, 2); // 30 + (0+4+2=6) + 20 + 15 = 71 → standard_ic
  assert.equal(t3, 71);
  assert.equal(b3, 'standard_ic');
});

console.log('\n증거 위생');

test('EvidencePack에 없는 sourceId 인용은 제거된다 (환각 인용 방어)', () => {
  const f = findings({ 'pi.unit': 2 });
  f.criteria[0].evidence = [
    { sourceId: 'note-1', quote: '진짜' },
    { sourceId: 'dart-99', quote: '없는 출처' },
  ];
  const s = scorePrinciple('physical_impact', f, pack);
  const ev = s.criteria.find((c) => c.criterionId === 'pi.unit')!.evidence;
  assert.equal(ev.length, 1);
  assert.equal(ev[0].sourceId, 'note-1');
});

test('에이전트가 기준을 누락하면 0점 + unknown 처리된다', () => {
  const s = scorePrinciple('structural_demand', findings({ 'sd.drivers': 3 }), pack);
  const missing = s.criteria.find((c) => c.criterionId === 'sd.subsidy')!;
  assert.equal(missing.score, 0);
  assert.equal(missing.verdict, 'unknown');
});

test('모든 원칙의 루브릭 배점 합이 선언된 max와 일치한다', () => {
  for (const id of PRINCIPLE_ORDER as PrincipleId[]) {
    const s = scorePrinciple(id, findings({}), pack);
    const sum = s.criteria.reduce((a, c) => a + c.max, 0);
    assert.equal(sum, s.max, `${id}: 세부 배점 합 ${sum} ≠ 원칙 배점 ${s.max}`);
  }
});

console.log(failed === 0 ? '\n전부 통과\n' : `\n${failed}건 실패\n`);
process.exit(failed === 0 ? 0 : 1);
