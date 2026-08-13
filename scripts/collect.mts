/**
 * 근거 수집 → runs/<기업>/evidence.md 로 저장.
 *   npm run collect -- "에스오에스랩"
 *
 * DART_API_KEY만 있으면 동작한다(무료). TAVILY_API_KEY는 선택 —
 * 없으면 Claude Code의 내장 WebSearch로 오케스트레이터가 보완한다.
 */

import { config } from 'dotenv';
import { mkdirSync, writeFileSync } from 'node:fs';
import { buildEvidencePack, renderEvidence } from '../lib/evidence/pack';
import { runDir, slugify } from '../lib/run-store';

config({ path: '.env.local', quiet: true });

const name = process.argv[2];
if (!name) {
  console.error('사용법: npm run collect -- "기업명" [주관사] [영문상호 ...]');
  process.exit(1);
}
const underwriter = process.argv[3];
// 3번째 이후 인자는 별칭(영문 상호 등)으로 취급한다
const aliases = process.argv.slice(4).filter(Boolean);

const dir = runDir(name);
mkdirSync(dir, { recursive: true });

const pack = await buildEvidencePack({ name, underwriter, aliases });

writeFileSync(`${dir}/evidence.md`, renderEvidence(pack), 'utf8');
writeFileSync(
  `${dir}/evidence.json`,
  JSON.stringify({ company: pack.company, gaps: pack.gaps, items: pack.items }, null, 2),
  'utf8',
);

const bySource = pack.items.reduce<Record<string, number>>((a, i) => {
  a[i.source] = (a[i.source] ?? 0) + 1;
  return a;
}, {});

console.log(`\n대상: ${name}${underwriter ? ` (주관사 ${underwriter})` : ''}`);
console.log(`수집: ${pack.items.length}건 ${JSON.stringify(bySource)}`);
console.log(`저장: ${dir}/evidence.md`);
if (pack.gaps.length) {
  console.log('\n공백:');
  for (const g of pack.gaps) console.log(`  ⚠ ${g}`);
}
console.log(`\nrun slug: ${slugify(name)}`);
