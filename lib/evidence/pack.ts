/**
 * Evidence Pack — 오케스트레이터가 **한 번만** 만들어서 4개 원칙 에이전트에 동일하게 주입한다.
 *
 * 왜 공유하는가:
 *  1) 4개 에이전트가 각자 크롤링하면 서로 다른 사실 위에서 점수를 매기게 되어 합산이 의미를 잃는다.
 *  2) 같은 근거 풀에서 판정해야 "왜 a는 높은데 b는 낮은가"를 IC에서 설명할 수 있다.
 *  3) 비용·시간이 4배로 줄어든다.
 */

import type { CompanyInput, EvidenceItem, EvidencePack } from '../contract';
import { collectDartEvidence } from './dart';
import { collectWebEvidence } from './web';

function chunkNotes(notes: string): EvidenceItem[] {
  const MAX = 4000;
  const out: EvidenceItem[] = [];
  for (let i = 0, n = 1; i < notes.length; i += MAX, n++) {
    out.push({
      id: `note-${n}`,
      source: 'user_note',
      title: `사용자 제공 자료 #${n}`,
      content: notes.slice(i, i + MAX),
    });
  }
  return out;
}

export async function buildEvidencePack(company: CompanyInput): Promise<EvidencePack> {
  const gaps: string[] = [];

  const [dart, web] = await Promise.all([
    collectDartEvidence(company.name, gaps, company.corpCode),
    collectWebEvidence(company, gaps),
  ]);

  const notes = company.notes?.trim() ? chunkNotes(company.notes.trim()) : [];
  if (!notes.length && !dart.length && !web.length) {
    gaps.push(
      '외부 근거를 전혀 확보하지 못했습니다. 모델 사전지식만으로는 판정하지 않으며 ' +
        '대부분의 기준이 unknown 처리됩니다.',
    );
  }

  const urlItems: EvidenceItem[] = (company.urls ?? [])
    .filter(Boolean)
    .map((u, i) => ({
      id: `url-${i + 1}`,
      source: 'web' as const,
      title: `사용자 지정 URL #${i + 1}`,
      url: u,
      content: `(사용자가 참고 URL로 지정: ${u})`,
    }));

  return { company, items: [...notes, ...dart, ...web, ...urlItems], gaps };
}

/** 에이전트 프롬프트에 넣을 형태로 직렬화. 인용 id를 눈에 띄게 붙인다. */
export function renderEvidence(pack: EvidencePack): string {
  if (pack.items.length === 0) return '(확보된 근거 없음)';
  return pack.items
    .map(
      (i) =>
        `<<<${i.id}>>>\n[출처: ${i.source}] ${i.title}${i.date ? ` (${i.date})` : ''}${
          i.url ? `\nURL: ${i.url}` : ''
        }\n${i.content}\n<<<END ${i.id}>>>`,
    )
    .join('\n\n');
}
