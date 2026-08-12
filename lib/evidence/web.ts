/**
 * 웹 검색 어댑터 (선택). TAVILY_API_KEY가 있으면 사용한다.
 *
 * 우리 철학상 웹 검색으로 잡아야 하는 것들:
 *  - 유상 PoC / 공급계약 / PO 보도자료  (b)
 *  - 제3자 시험성적서 · 인증 · 기술성 평가 등급  (d-A)
 *  - 등록 특허, 논문, 창업자 이력  (d-B)
 *  - 대체 대상 설비/원료, 저감 규모 수치  (c)
 *
 * 키가 없으면 조용히 비우고 gaps에 남긴다. (없는 근거를 지어내지 않기 위함)
 */

import type { EvidenceItem, CompanyInput } from '../contract';

type TavilyResult = { title: string; url: string; content: string; published_date?: string };

function queriesFor(c: CompanyInput): string[] {
  const n = c.name;
  return [
    `${n} 공급계약 수주 양산 PO`,
    `${n} 유상 PoC 실증 고객 도입`,
    `${n} 특허 기술성평가 인증 시험성적서`,
    `${n} 창업자 대표 연구 이력 논문`,
    `${n} 감축 절감 효율 대비 기존 공정`,
    c.underwriter ? `${n} ${c.underwriter} 기술특례 상장 예비심사` : `${n} IPO 상장 예비심사`,
  ];
}

export async function collectWebEvidence(
  company: CompanyInput,
  gaps: string[],
): Promise<EvidenceItem[]> {
  const key = process.env.TAVILY_API_KEY;
  if (!key) {
    gaps.push(
      'TAVILY_API_KEY 미설정 — 뉴스·보도자료·특허 등 공개 웹 증거를 수집하지 못했습니다. ' +
        '수동 입력(참고자료 붙여넣기)으로 보완하세요.',
    );
    return [];
  }

  const items: EvidenceItem[] = [];
  const seen = new Set<string>();

  /**
   * 관련성 필터. 검색어에 회사명을 넣어도 검색엔진이 일반론 글을 물어온다
   * (예: "유상 PoC의 중요성" 같은 칼럼). 근거 풀에 섞이면 에이전트가 그 기업의
   * 사실인 것처럼 인용할 수 있으므로, 회사명이 실제로 언급된 문서만 남긴다.
   */
  const needle = company.name.replace(/\s|\(주\)|주식회사|㈜/g, '').toLowerCase();
  const mentionsCompany = (r: TavilyResult) =>
    `${r.title} ${r.content}`.replace(/\s/g, '').toLowerCase().includes(needle);
  let dropped = 0;

  const settled = await Promise.allSettled(
    queriesFor(company).map(async (q) => {
      const res = await fetch('https://api.tavily.com/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
        body: JSON.stringify({
          query: q,
          search_depth: 'advanced',
          max_results: 4,
          include_answer: false,
        }),
      });
      if (!res.ok) throw new Error(`Tavily ${res.status}`);
      const json = (await res.json()) as { results?: TavilyResult[] };
      return json.results ?? [];
    }),
  );

  for (const s of settled) {
    if (s.status !== 'fulfilled') continue;
    for (const r of s.value) {
      if (seen.has(r.url)) continue;
      seen.add(r.url);
      if (!mentionsCompany(r)) {
        dropped++;
        continue;
      }
      items.push({
        id: `web-${items.length + 1}`,
        source: 'web',
        title: r.title,
        url: r.url,
        date: r.published_date?.slice(0, 10),
        content: r.content.slice(0, 2500),
      });
    }
  }

  if (items.length === 0) gaps.push('웹 검색 결과가 비어 있습니다.');
  if (dropped > 0) {
    gaps.push(`웹 검색 결과 ${dropped}건은 기업명이 언급되지 않아 관련성 필터에서 제외했습니다.`);
  }
  return items;
}
