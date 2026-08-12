"""DART 공시 원문에서 결정론적 규칙으로 Evidence 후보를 뽑는다.

**무엇을 뽑을 수 있고 없는가.**

2026-08-13에 실제 rcept_no로 `DartClient.fetch_document`를 라이브 호출해 아래 두 항목의
표준 서식을 확인했다. 사업보고서·분기보고서 "II. 사업의 내용 › 8. 연구개발활동" 섹션은
전자공시 표준 서식이라 회사마다 표 구조가 거의 동일하다:

- `B2_registered_patents` — "지적재산권 보유현황" 표. 구분(등록/출원 중/합계) ×
  국내특허/해외특허/총계 열. "등록" 행의 "총계" 열이 등록 특허 건수다 (심텍 2025.09
  분기보고서에서 확인, 등록 144건).
- `B3_domain_expertise` — "[연구개발 인력 구성]" 표. 학력(박사/석사/학사/기타) × 인원수
  행. (박사+석사)/합계로 비중을 계산한다 (루닛 2025.09 분기보고서에서 확인, 박사 20·석사
  67·학사 90·기타 7 → 184명 중 47.3%).

**뽑을 수 없다고 판단해 뺀 것.**

- `B1_exchange_tech_grade` — 브리핑 문서는 "기술특례상장 관련 공시의 기술평가 등급"을
  가능하다고 가정했지만, 라이브 확인 결과 사업/분기보고서 본문에서 "기술평가"라는 단어는
  기관명("한국산업기술평가관리원")이나 연구과제명의 일부로만 나타났고, 거래소 기술성
  평가등급(A·BBB 등) 문자열로는 한 번도 나타나지 않았다. 그 등급은 상장 시점의
  증권신고서/투자설명서에 있는데, DART list.json으로 신뢰성 있게 짚어내려면 상장일 근처
  공시를 별도로 특정해야 하고 등급 문자열 자체가 자유 서식이라 오탐(다른 숫자·등급을
  잘못 집어 MET)의 위험이 이 태스크가 가장 경계하는 실패 모드다. 추측성 규칙을 만드는
  대신 이 항목은 md 지시서(사용자의 LLM 조사)로 넘긴다.
- `A1` `A2` `A3` `B4` `C1` `C2` `C3` — 공시 원문에 존재하지 않는 정보다 (PoC 재현성,
  제3자 시험성적서, 실환경 가동시간, 랩·논문 이력, 증설 계획, capex 조달, 공급망 등).

규칙이 만드는 Evidence는 **후보**다. 표를 찾았고 숫자를 명확히 읽었을 때만 만든다.
숫자를 읽었고 임계치에 못 미치면 `NOT_MET`을 낸다 (이건 추측이 아니라 판독이다).
표 자체를 못 찾았거나 구조가 애매하면 아무것도 만들지 않고 경고만 남긴다 —
`UNVERIFIABLE`로 남아 실사 질문이 되는 것이 맞는 결과다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from agents.proven_scalability.schema import CriterionId, Evidence, Status
from agents.proven_scalability.tools.dart import DartClient, DartError

#: DART 뷰어 URL. Evidence.source_url은 사람이 원문을 다시 찾아갈 수 있어야 한다.
_VIEWER_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

#: 정기공시(사업보고서·분기보고서·반기보고서) — B2·B3 표의 표준 서식이 있는 곳.
_KIND_PERIODIC = "A"
#: 외부감사관련(감사보고서·연결감사보고서) — 비상장 기업은 사업보고서 의무가 없어
#: 이것만 내는 경우가 많다(범한메카텍 실사로 확인, 2026-08-13). B2·B3 표는 없지만
#: 계약부채·수주잔고 같은 Economic Value 신호가 주석에 있을 수 있어 본다.
_KIND_AUDIT = "F"
_BEGIN_DATE = "20220101"
_END_DATE = "20261231"
#: 최근 공시부터 몇 건까지 훑을지. 너무 크면 매 실행마다 문서를 여러 건 내려받는다.
#: DART list.json의 pblntf_ty는 한 번에 값 하나만 받는다(콤마로 묶어 넘겨도 해당 유형
#: 없음으로 취급됨을 라이브 확인) — 그래서 A·F를 별도 호출 두 번으로 조회해 합친다.
#: 문서 조회(fetch_document) 횟수는 이 상수로 그대로 묶여 있다 — list.json 호출이
#: 하나 늘 뿐 실제 문서 다운로드 비용은 늘지 않는다.
_MAX_DOCUMENTS = 5

#: 감사보고서 주석에서 자주 보이는, Economic Value 축(원칙 b) 신호. 우리 축(기술성)의
#: Evidence는 아니다 — 팀원에게 넘기는 메모만 남긴다.
_ECONOMIC_VALUE_KEYWORDS = ("계약부채", "수주잔고", "건설형공사계약")

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _flatten(raw: str) -> str:
    """태그를 공백으로 치환하고 연속 공백을 접어 표를 평문으로 만든다.

    실제 공시 XML은 TD 속성이 회사마다 제각각이라(WIDTH·USERMARK 등) 태그를 남긴 채
    정규식을 짜면 회사마다 깨진다. 평문으로 만들면 "등록 141건 3건 144건" 처럼 표의
    의미만 남는다.
    """
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", raw)).strip()


@dataclass(frozen=True)
class Parsed:
    status: Status
    extracted_value: str
    quote: str


ParseFn = Callable[[str], "Parsed | None"]


@dataclass(frozen=True)
class Rule:
    criterion_id: CriterionId
    #: 문서 원문에서 이 섹션을 찾는 키워드들. 먼저 찾은 것을 쓴다.
    keywords: tuple[str, ...]
    #: 키워드 위치부터 이만큼의 원문(raw, 태그 포함)을 파서에 넘긴다.
    window: int
    parser: ParseFn


# --- B2: 지적재산권 보유현황 표 ---
#
# "구분 | 국내특허 | 해외특허 | 총계" 헤더에 "등록 / 출원 중 / 합계" 행이 오는 표준 서식.
# "등록" 행의 세 번째(총계) 칸이 등록 특허 건수다. 국내+해외 합이 총계와 일치할 때만
# 확신한다 — 안 맞으면 표를 잘못 짚었다는 뜻이므로 아무것도 내지 않는다.
_PATENT_ROW_RE = re.compile(r"등록\s*([\d,]+)\s*건\s*([\d,]+)\s*건\s*([\d,]+)\s*건")
_PATENT_THRESHOLD = 3  # criteria.py B2_registered_patents: "등록 특허 3건 이상"


def _parse_patents(raw_window: str) -> Parsed | None:
    flat = _flatten(raw_window)
    match = _PATENT_ROW_RE.search(flat)
    if match is None:
        return None

    domestic, foreign, total = (int(g.replace(",", "")) for g in match.groups())
    if total != domestic + foreign:
        # 표를 잘못 짚었을 가능성 — 국내+해외가 총계와 안 맞으면 확신할 수 없다.
        return None

    status: Status = "MET" if total >= _PATENT_THRESHOLD else "NOT_MET"
    quote_start = max(0, match.start() - 20)
    quote = flat[quote_start : match.end()][:300]
    return Parsed(status=status, extracted_value=f"등록 특허 {total}건", quote=quote)


# --- B3: 연구개발 인력 구성 표 ---
#
# "학력" 헤더 뒤에 박사/석사/학사/기타 등 학위별 헤더가 오고, "인원수" 행에 그만큼의
# 숫자가 온다. 헤더 개수와 숫자 개수가 다르면(표를 잘못 짚었거나 형식이 다르면) 포기한다.
# "박사"·"석사" 헤더가 둘 다 있어야 비중을 계산할 수 있다.
_RND_HEADER_RE = re.compile(r"학력((?:\s+[^\s\d]{1,10}){1,8})\s*인원수((?:\s+[\d,]{1,10}){1,8})")
_RND_THRESHOLD = 0.6  # criteria.py B3_domain_expertise: "석사 이상 인력 비중 60% 이상"


def _parse_rnd_personnel(raw_window: str) -> Parsed | None:
    flat = _flatten(raw_window)
    match = _RND_HEADER_RE.search(flat)
    if match is None:
        return None

    headers = match.group(1).split()
    values_raw = match.group(2).split()
    if len(headers) != len(values_raw) or not headers:
        return None

    try:
        values = [int(v.replace(",", "")) for v in values_raw]
    except ValueError:
        return None

    counts = dict(zip(headers, values))
    if "박사" not in counts or "석사" not in counts:
        # 학위 구분 자체가 다른 표(예: 성별·근속연수 표)일 수 있다 — 확신할 수 없다.
        return None

    total = sum(counts.values())
    if total <= 0:
        return None

    advanced = counts["박사"] + counts["석사"]
    ratio = advanced / total
    status: Status = "MET" if ratio >= _RND_THRESHOLD else "NOT_MET"
    pct = round(ratio * 100, 1)
    quote = flat[match.start() : match.end()][:300]
    extracted_value = f"석사 이상 {pct}% (박사 {counts['박사']}+석사 {counts['석사']} / 총 {total}명)"
    return Parsed(status=status, extracted_value=extracted_value, quote=quote)


#: 이 튜플에 없는 criterion_id는 어떤 입력이 와도 Evidence가 생기지 않는다 — 그게
#: A1·A2·A3·B1·B4·C1·C2·C3의 정직한 상태다 (md 지시서 또는 실사의 몫).
RULES: tuple[Rule, ...] = (
    Rule(
        criterion_id="B2_registered_patents",
        keywords=(
            "지적재산권 보유현황",
            "산업재산권 보유현황",
            "특허 보유현황",
            # 아래 둘은 표가 아니라 서술형으로만 언급하는 회사(예: 삼성전자)를 위한
            # 폴백이다. 표를 못 찾으면 _parse_patents가 None을 돌려주고, extract()가
            # 그걸 '섹션은 찾았지만 못 읽었다' 경고로 남긴다 — 추측하지 않는다.
            "지적재산권",
            "산업재산권",
        ),
        window=4000,
        parser=_parse_patents,
    ),
    Rule(
        criterion_id="B3_domain_expertise",
        keywords=("연구개발 인력 구성", "연구개발 인력"),
        window=4000,
        parser=_parse_rnd_personnel,
    ),
)


def extract(client: DartClient, company: str) -> tuple[list[Evidence], list[str]]:
    """회사의 최근 정기공시를 훑어 RULES를 적용한다.

    Returns:
        (Evidence 리스트, 경고 리스트). 실패·모호함은 예외가 아니라 경고로 표현한다 —
        DART 규칙 추출 실패가 전체 판정을 죽여서는 안 된다.
    """
    warnings: list[str] = []

    try:
        candidates = client.find_corp_candidates(company)
    except DartError as exc:
        warnings.append(f"DART 법인 조회 실패: {exc}")
        return [], warnings

    if not candidates:
        warnings.append(f"DART에서 '{company}'을(를) 찾지 못했다 — 공시 자체가 없다.")
        return [], warnings

    corp_name, corp_code = candidates[0]
    if corp_name != company and len(candidates) > 1:
        # dart_search(tools/dart.py)와 같은 원칙: 정확 일치가 없고 후보가 여럿이면
        # 몰래 하나를 고르지 않는다. 잘못된 법인의 특허·인력 수는 tier 1로 기록되고
        # 아무도 그 오류를 볼 수 없다.
        warnings.append(
            f"'{company}'과 정확히 일치하는 법인이 DART에 없고 후보가 {len(candidates)}건이다. "
            "법인을 확정한 뒤 다시 시도할 것 — DART 규칙 추출을 건너뛴다."
        )
        return [], warnings

    rows_periodic, list_warning = _list_disclosures_safe(
        client, corp_code, _KIND_PERIODIC, "정기공시"
    )
    if list_warning:
        warnings.append(list_warning)

    rows_audit, list_warning = _list_disclosures_safe(client, corp_code, _KIND_AUDIT, "외부감사관련")
    if list_warning:
        warnings.append(list_warning)

    if not rows_periodic and not rows_audit:
        # 상태 1: 이 법인은 DART에 아무 공시도 없다.
        warnings.append(f"{corp_name}은(는) DART에 공시가 전혀 없다 — 정기공시·외부감사관련 모두 0건.")
        return [], warnings

    combined = _merge_by_date(rows_periodic, rows_audit)

    evidence: list[Evidence] = []
    matched: set[str] = set()
    economic_value_noted = False

    for row in combined[:_MAX_DOCUMENTS]:
        rcept_no = row.get("rcept_no")
        if not rcept_no:
            continue
        try:
            text = client.fetch_document(rcept_no)
        except DartError as exc:
            warnings.append(f"{corp_name} {rcept_no} 문서 조회 실패: {exc}")
            continue

        if not economic_value_noted:
            hit = next((kw for kw in _ECONOMIC_VALUE_KEYWORDS if kw in text), None)
            if hit is not None:
                warnings.append(
                    f"{corp_name} {rcept_no}: '{hit}' 등 Economic Value 축(원칙 b) 신호가 "
                    "감사보고서 주석에 있다 — 이 축(기술성)의 Evidence로는 만들지 않는다. "
                    "해당 축을 담당하는 에이전트에게 전달할 것."
                )
                economic_value_noted = True

        for rule in RULES:
            if rule.criterion_id in matched:
                continue
            index = _find_first(text, rule.keywords)
            if index is None:
                continue
            window_text = text[index : index + rule.window]
            parsed = rule.parser(window_text)
            if parsed is None:
                warnings.append(
                    f"{corp_name} {rcept_no}: '{rule.criterion_id}' 관련 섹션은 찾았지만 "
                    "표를 명확히 읽지 못했다 — 추측하지 않고 건너뛴다 (UNVERIFIABLE로 남는다)."
                )
                continue
            evidence.append(
                Evidence(
                    criterion_id=rule.criterion_id,
                    status=parsed.status,
                    source_tier=1,
                    source_url=_VIEWER_URL.format(rcept_no=rcept_no),
                    quote=parsed.quote,
                    extracted_value=parsed.extracted_value,
                )
            )
            matched.add(rule.criterion_id)

        if len(matched) == len(RULES):
            break

    if not matched and not rows_periodic:
        # 상태 2: 공시는 있지만 우리 규칙이 읽을 수 있는 유형이 하나도 없다 —
        # 비상장 기업이 감사보고서만 내고 사업보고서가 아예 없는 경우가 정상 형태다.
        # 특허·연구개발 인력 표는 사업보고서에만 있으므로 DART로는 확인할 수 없다.
        missing = ", ".join(rule.criterion_id for rule in RULES)
        warnings.append(
            f"{corp_name}의 DART 공시는 외부감사관련(감사보고서) {len(rows_audit)}건뿐이고 "
            "정기공시(사업보고서·분기보고서)가 없다. 특허 보유현황·연구개발 인력 구성 표는 "
            "사업보고서에만 있어, 비상장 기업이 감사보고서만 제출한 경우 DART로는 확인할 수 "
            f"없다 — {missing}는 md 지시서(사용자 LLM 조사) 경로로 조사할 것."
        )

    return evidence, warnings


def _list_disclosures_safe(
    client: DartClient, corp_code: str, kind: str, label: str
) -> tuple[list[dict], str | None]:
    """list_disclosures를 감싸 실패를 예외 대신 경고 문자열로 돌려준다."""
    try:
        return client.list_disclosures(corp_code, _BEGIN_DATE, _END_DATE, kind=kind), None
    except DartError as exc:
        return [], f"DART {label} 목록 조회 실패: {exc}"


def _merge_by_date(rows_a: list[dict], rows_b: list[dict]) -> list[dict]:
    """두 kind의 결과를 rcept_no로 중복 제거하고 접수일 최신순으로 합친다."""
    seen: set[str] = set()
    merged: list[dict] = []
    for row in sorted(rows_a + rows_b, key=lambda r: r.get("rcept_dt", ""), reverse=True):
        rcept_no = row.get("rcept_no")
        if not rcept_no or rcept_no in seen:
            continue
        seen.add(rcept_no)
        merged.append(row)
    return merged


def _find_first(text: str, keywords: tuple[str, ...]) -> int | None:
    for keyword in keywords:
        index = text.find(keyword)
        if index != -1:
            return index
    return None
