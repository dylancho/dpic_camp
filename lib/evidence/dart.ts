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

type Corp = { code: string; name: string };

/** 정규화 상호 → 같은 이름을 가진 법인 **전부**. 동명이인을 조용히 삼키지 않는다. */
let corpCodeCache: Map<string, Corp[]> | null = null;

async function loadCorpCodes(apiKey: string) {
  if (corpCodeCache) return corpCodeCache;
  const res = await fetch(`${BASE}/corpCode.xml?crtfc_key=${apiKey}`);
  if (!res.ok) throw new Error(`DART corpCode 조회 실패: ${res.status}`);
  const xml = unzipFirstEntry(Buffer.from(await res.arrayBuffer())).toString('utf8');

  const map = new Map<string, Corp[]>();
  const re = /<list>\s*<corp_code>(.*?)<\/corp_code>\s*<corp_name>(.*?)<\/corp_name>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml))) {
    const name = m[2].trim();
    const key = normalize(name);
    const arr = map.get(key);
    if (arr) arr.push({ code: m[1].trim(), name });
    else map.set(key, [{ code: m[1].trim(), name }]);
  }
  corpCodeCache = map;
  return map;
}

function normalize(s: string) {
  return s.replace(/\s|\(주\)|주식회사|㈜/g, '').toLowerCase();
}

/** DART 기업개황 — 신원 대조용(설립일·업종·주소·대표). 동명이인 판별의 근거가 된다. */
export async function fetchCompanyProfile(corpCode: string, apiKey: string) {
  const res = await fetch(`${BASE}/company.json?crtfc_key=${apiKey}&corp_code=${corpCode}`);
  if (!res.ok) return null;
  const j = (await res.json()) as Record<string, string>;
  if (j.status !== '000') return null;
  return {
    corpName: j.corp_name,
    estDt: j.est_dt,
    indutyCode: j.induty_code,
    address: j.adres,
    ceo: j.ceo_nm,
    stockCode: j.stock_code,
  };
}

/**
 * 상호로 법인을 찾는다. **동명이인이면 고르지 않고 전부 돌려준다.**
 *
 * 실제로 터진 사고: "에이치투"로 조회하면 DART에 완전히 같은 이름의 법인이 2개 있는데
 * (석유화학 도매업체 / 금속재생 업체), 예전 구현은 먼저 만난 것을 조용히 골랐다.
 * 그 결과 VRFB ESS 기업을 심사하면서 무관한 수입·유통 회사의 감사보고서를 근거로 썼다.
 * 잘못된 근거는 근거 없음보다 나쁘다 — 점수가 그럴듯하게 나와서 아무도 의심하지 않기 때문이다.
 */
export async function findCorpCandidates(companyName: string, apiKey: string): Promise<Corp[]> {
  const map = await loadCorpCodes(apiKey);
  const key = normalize(companyName);
  const exact = map.get(key);
  if (exact?.length) return exact;
  if (key.length < 2) return [];
  // 부분 일치 폴백 — 여기서도 여러 건이면 전부 돌려준다
  const partial: Corp[] = [];
  for (const [k, v] of map) {
    if (k.includes(key)) partial.push(...v);
    if (partial.length > 8) break;
  }
  return partial;
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
  corpCodeOverride?: string,
): Promise<EvidenceItem[]> {
  const apiKey = process.env.DART_API_KEY;
  if (!apiKey) {
    gaps.push('DART_API_KEY 미설정 — 공시(수주잔고·계약부채) 기반 상업 증거를 확인하지 못했습니다.');
    return [];
  }

  try {
    let corp: Corp;
    if (corpCodeOverride) {
      corp = { code: corpCodeOverride, name: companyName };
    } else {
      const candidates = await findCorpCandidates(companyName, apiKey);
      if (candidates.length === 0) {
        gaps.push(`DART에서 "${companyName}" 고유번호를 찾지 못했습니다 (미등록 법인이거나 상호 불일치).`);
        return [];
      }
      if (candidates.length > 1) {
        // 동명이인을 임의로 고르면 무관한 회사의 재무제표로 심사하게 된다.
        // 잘못된 근거는 근거 없음보다 나쁘므로, 고르지 않고 수집을 중단한다.
        const profiles = await Promise.all(
          candidates.slice(0, 6).map(async (c) => {
            const p = await fetchCompanyProfile(c.code, apiKey);
            return `    ${c.code}  ${c.name}` +
              (p ? ` — 설립 ${p.estDt}, 업종 ${p.indutyCode}, 대표 ${p.ceo}, ${p.address?.slice(0, 30)}` : '');
          }),
        );
        gaps.push(
          `⛔ DART에 "${companyName}" 과 일치하는 법인이 ${candidates.length}건입니다. ` +
            `임의로 고르면 무관한 회사의 재무제표로 심사하게 되므로 DART 수집을 중단했습니다.\n` +
            profiles.join('\n') +
            `\n    → 맞는 법인을 골라 다시 수집하세요: npm run collect -- "${companyName}" "" --corp-code=<8자리>`,
        );
        return [];
      }
      corp = candidates[0];
    }

    // 신원 대조용 개황을 항상 첫 근거로 넣는다. 에이전트가 "이게 정말 그 회사인가"를
    // 설립일·업종·주소로 직접 확인할 수 있어야 한다.
    const profile = await fetchCompanyProfile(corp.code, apiKey);
    const profileItem: EvidenceItem | null = profile
      ? {
          id: 'dart-profile',
          source: 'dart',
          title: `[DART] ${profile.corpName} 기업개황 (신원 대조용)`,
          url: `https://dart.fss.or.kr/dsae001/selectPopup.ax?selectKey=${corp.code}`,
          content:
            `상호: ${profile.corpName}\n고유번호: ${corp.code}\n설립일: ${profile.estDt}\n` +
            `업종코드: ${profile.indutyCode}\n대표자: ${profile.ceo}\n주소: ${profile.address}\n` +
            `종목코드: ${profile.stockCode || '(비상장)'}\n\n` +
            `※ 이 개황이 심사 대상 기업과 일치하는지 먼저 확인하라. ` +
            `설립연도·업종·주소가 어긋나면 동명이인일 수 있으며, 그 경우 아래 dart-* 근거를 사용하면 안 된다.`,
        }
      : null;

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
      return profileItem ? [profileItem] : [];
    }

    // 감사보고서 · 사업보고서 · 분기/반기보고서 우선
    const priority = /감사보고서|사업보고서|반기보고서|분기보고서|증권신고서|투자설명서/;
    const targets = list.list.filter((d) => priority.test(d.report_nm)).slice(0, 3);
    if (targets.length === 0) targets.push(list.list[0]);

    const items: EvidenceItem[] = profileItem ? [profileItem] : [];
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

    if (items.filter((i) => /^dart-\d+$/.test(i.id)).length === 0) {
      gaps.push('DART 공시 원문 본문을 추출하지 못했습니다 (목록만 확보).');
    }
    if (profile) {
      gaps.push(
        `DART 신원 대조 필요: 고유번호 ${corp.code} / 설립 ${profile.estDt} / 업종 ${profile.indutyCode} / ` +
          `대표 ${profile.ceo}. 심사 대상 기업과 어긋나면 dart-* 근거를 사용하지 말 것 (dart-profile 참조).`,
      );
    }
    return items;
  } catch (e) {
    gaps.push(`DART 수집 실패: ${(e as Error).message}`);
    return [];
  }
}
