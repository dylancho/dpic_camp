/**
 * DART OpenAPI 어댑터.
 *
 * 왜 필요한가: 우리 철학의 b. Economic Value는 "데이터를 구할 수 없는 경우 DART 감사보고서 **주석**에
 * 명시된 수주잔고 / 계약부채 / 건설형공사계약 항목의 추이로 판단"하라고 규정한다.
 * pre-IPO 외감법인은 감사보고서를 DART에 제출하므로, 여기가 유일하게 '돈이 오간 증거'를 잡을 수 있는 곳이다.
 *
 * 필요 환경변수: DART_API_KEY (https://opendart.fss.or.kr 에서 무료 발급)
 * 키가 없으면 조용히 빈 배열을 반환하고 gaps에 사유를 남긴다.
 */

import { unzipFirstEntry } from './zip';
import type { EvidenceItem } from '../contract';

const BASE = 'https://opendart.fss.or.kr/api';

/** 주석에서 찾아낼 키워드 — 상업 증거의 물증 */
const NOTE_KEYWORDS = [
  '수주잔고',
  '계약부채',
  '건설형공사계약',
  '진행률',
  '선수금',
  '매출액',
  '주요 매출처',
  '특수관계자',
  '연구개발비',
  '무형자산',
];

let corpCodeCache: Map<string, { code: string; name: string }> | null = null;

async function loadCorpCodes(apiKey: string) {
  if (corpCodeCache) return corpCodeCache;
  const res = await fetch(`${BASE}/corpCode.xml?crtfc_key=${apiKey}`);
  if (!res.ok) throw new Error(`DART corpCode 조회 실패: ${res.status}`);
  const xml = unzipFirstEntry(Buffer.from(await res.arrayBuffer())).toString('utf8');

  const map = new Map<string, { code: string; name: string }>();
  const re = /<list>\s*<corp_code>(.*?)<\/corp_code>\s*<corp_name>(.*?)<\/corp_name>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml))) {
    const name = m[2].trim();
    // 동명이인 방지: 먼저 등록된 것을 유지 (DART는 최근 등록 순이 아님)
    const key = normalize(name);
    if (!map.has(key)) map.set(key, { code: m[1].trim(), name });
  }
  corpCodeCache = map;
  return map;
}

function normalize(s: string) {
  return s.replace(/\s|\(주\)|주식회사|㈜/g, '').toLowerCase();
}

export async function findCorpCode(companyName: string, apiKey: string) {
  const map = await loadCorpCodes(apiKey);
  const key = normalize(companyName);
  if (map.has(key)) return map.get(key)!;
  // 부분 일치 폴백
  for (const [k, v] of map) {
    if (k.includes(key) && key.length >= 2) return v;
  }
  return null;
}

/** 공시 원문(document.xml)을 받아 태그를 제거하고 키워드 주변만 잘라낸다 */
async function fetchDocumentExcerpt(rceptNo: string, apiKey: string, maxChars = 6000) {
  const res = await fetch(`${BASE}/document.xml?crtfc_key=${apiKey}&rcept_no=${rceptNo}`);
  if (!res.ok) return null;
  const raw = Buffer.from(await res.arrayBuffer());
  let text: string;
  try {
    text = unzipFirstEntry(raw).toString('utf8');
  } catch {
    return null;
  }

  const plain = text
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const chunks: string[] = [];
  for (const kw of NOTE_KEYWORDS) {
    let idx = plain.indexOf(kw);
    let hits = 0;
    while (idx >= 0 && hits < 2) {
      chunks.push(plain.slice(Math.max(0, idx - 250), idx + 550));
      hits++;
      idx = plain.indexOf(kw, idx + 550);
    }
  }
  if (chunks.length === 0) return plain.slice(0, maxChars);
  return chunks.join('\n---\n').slice(0, maxChars);
}

export async function collectDartEvidence(
  companyName: string,
  gaps: string[],
): Promise<EvidenceItem[]> {
  const apiKey = process.env.DART_API_KEY;
  if (!apiKey) {
    gaps.push('DART_API_KEY 미설정 — 공시(수주잔고·계약부채) 기반 상업 증거를 확인하지 못했습니다.');
    return [];
  }

  try {
    const corp = await findCorpCode(companyName, apiKey);
    if (!corp) {
      gaps.push(`DART에서 "${companyName}" 고유번호를 찾지 못했습니다 (미등록 법인이거나 상호 불일치).`);
      return [];
    }

    const end = new Date();
    const bgn = new Date(end.getFullYear() - 3, end.getMonth(), end.getDate());
    const fmt = (d: Date) => d.toISOString().slice(0, 10).replace(/-/g, '');

    const listUrl =
      `${BASE}/list.json?crtfc_key=${apiKey}&corp_code=${corp.code}` +
      `&bgn_de=${fmt(bgn)}&end_de=${fmt(end)}&page_count=100`;
    const listRes = await fetch(listUrl);
    const list = (await listRes.json()) as {
      status: string;
      message: string;
      list?: { report_nm: string; rcept_no: string; rcept_dt: string; corp_name: string }[];
    };

    if (list.status !== '000' || !list.list?.length) {
      gaps.push(`DART 공시 목록이 비어 있습니다 (status=${list.status}: ${list.message}).`);
      return [];
    }

    // 감사보고서 · 사업보고서 · 분기/반기보고서 우선
    const priority = /감사보고서|사업보고서|반기보고서|분기보고서|증권신고서|투자설명서/;
    const targets = list.list.filter((d) => priority.test(d.report_nm)).slice(0, 3);
    if (targets.length === 0) targets.push(list.list[0]);

    const items: EvidenceItem[] = [];
    for (const [i, doc] of targets.entries()) {
      const excerpt = await fetchDocumentExcerpt(doc.rcept_no, apiKey);
      if (!excerpt) continue;
      items.push({
        id: `dart-${i + 1}`,
        source: 'dart',
        title: `[DART] ${doc.corp_name} ${doc.report_nm}`,
        url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${doc.rcept_no}`,
        date: `${doc.rcept_dt.slice(0, 4)}-${doc.rcept_dt.slice(4, 6)}-${doc.rcept_dt.slice(6, 8)}`,
        content: excerpt,
      });
    }

    // 공시 목록 자체도 하나의 증거 (제출 이력 = 외감 대상 여부, 증권신고서 = IPO 진행 상태)
    items.push({
      id: `dart-index`,
      source: 'dart',
      title: `[DART] ${corp.name} 최근 3년 공시 목록`,
      url: `https://dart.fss.or.kr/dsab007/main.do`,
      content: list.list
        .slice(0, 40)
        .map((d) => `${d.rcept_dt} ${d.report_nm}`)
        .join('\n'),
    });

    if (items.length === 1) {
      gaps.push('DART 공시 원문 본문을 추출하지 못했습니다 (목록만 확보).');
    }
    return items;
  } catch (e) {
    gaps.push(`DART 수집 실패: ${(e as Error).message}`);
    return [];
  }
}
