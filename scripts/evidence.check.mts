/**
 * 근거 수집 파이프라인 점검 (LLM 호출 없음).
 *   npx tsx scripts/evidence.check.ts "기업명"
 *
 * DART 고유번호 조회 → 공시 원문 zip 해제 → 주석 키워드 추출, 웹 검색까지 실제로 확인한다.
 */

import { config } from 'dotenv';
config({ path: '.env.local' });

import { buildEvidencePack } from '../lib/evidence/pack';

const name = process.argv[2] ?? '에스오에스랩';

console.log(`\n대상: ${name}`);
console.log('키 상태:', {
  DART: process.env.DART_API_KEY ? 'set' : 'MISSING',
  TAVILY: process.env.TAVILY_API_KEY ? 'set' : 'MISSING',
});

const t0 = Date.now();
const pack = await buildEvidencePack({ name });
console.log(`\n소요 ${((Date.now() - t0) / 1000).toFixed(1)}s · 근거 ${pack.items.length}건\n`);

for (const i of pack.items) {
  console.log(`[${i.id}] (${i.source}) ${i.title}`);
  if (i.url) console.log(`      ${i.url}`);
  console.log(`      ${i.content.slice(0, 180).replace(/\s+/g, ' ')}…`);
  console.log(`      (본문 ${i.content.length}자)\n`);
}

if (pack.gaps.length) {
  console.log('공백:');
  for (const g of pack.gaps) console.log(`  ⚠ ${g}`);
}

const bySource = pack.items.reduce<Record<string, number>>((a, i) => {
  a[i.source] = (a[i.source] ?? 0) + 1;
  return a;
}, {});
console.log('\n출처별:', bySource);
