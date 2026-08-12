"""DART OpenAPI 클라이언트와 리서처용 툴.

API 키는 절대 예외 메시지나 로그에 담지 않는다.
"""

from __future__ import annotations

import io
import json
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import httpx
from anthropic import beta_tool

_BASE = "https://opendart.fss.or.kr/api"
_CACHE = Path.home() / ".cache" / "dpic" / "corp_codes.json"

#: 조회 결과 없음. 에러가 아니라 빈 결과다.
_STATUS_NO_DATA = "013"
_STATUS_OK = "000"


class DartError(Exception):
    """DART가 비정상 status를 반환했을 때. 메시지에 API 키를 담지 않는다."""


class DartClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=30.0)

    def close(self) -> None:
        """이 클라이언트가 소유한 연결 풀을 닫는다."""
        self._http.close()

    def _request(self, path: str, **params: str) -> httpx.Response:
        """DART에 GET을 보내고 응답을 반환한다. non-2xx는 DartError로 변환한다.

        HTTPStatusError.__str__은 request.url을 담고, url에는 crtfc_key가
        들어 있으므로 절대 str(exc)나 response.url을 노출하지 않는다.
        """
        response = self._http.get(
            f"{_BASE}/{path}", params={"crtfc_key": self._key, **params}
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DartError(f"DART HTTP {exc.response.status_code}") from None
        return response

    def _get_json(self, path: str, **params: str) -> dict:
        response = self._request(path, **params)
        payload = response.json()
        status = payload.get("status")
        if status == _STATUS_NO_DATA:
            return {}
        if status != _STATUS_OK:
            # payload["message"]만 담는다. params에는 키가 들어 있으므로 쓰지 않는다
            raise DartError(f"DART status {status}: {payload.get('message', '')}")
        return payload

    def _read_zip_first_entry(self, content: bytes, what: str) -> bytes:
        """zip 응답에서 첫 엔트리를 꺼낸다. 빈 zip이나 zip이 아닌 응답을 DartError로 변환한다."""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = archive.namelist()
                if not names:
                    raise DartError(f"DART {what} 응답이 빈 zip이다")
                return archive.read(names[0])
        except zipfile.BadZipFile:
            raise DartError(f"DART {what} 응답이 zip 형식이 아니다") from None

    def find_corp_candidates(self, company_name: str) -> list[tuple[str, str]]:
        """회사명에 해당할 수 있는 (법인명, 고유번호) 후보를 우선순위대로 돌려준다.

        정확 일치 > 접두 일치 > 부분 일치, 각 구간에서는 짧은 이름이 앞이다.
        XML 문서 순서 첫 히트를 쓰면 '심텍' 조회가 '심텍홀딩스'로 풀릴 수 있고,
        그렇게 나온 근거는 tier 1(공시)로 기록되므로 되돌릴 수 없다.
        정확 일치가 있으면 그것만 돌려준다 — 다른 후보를 볼 이유가 없다.
        """
        table = self._corp_code_table()
        exact = table.get(company_name)
        if exact:
            return [(company_name, exact)]

        def by_length(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
            return sorted(pairs, key=lambda pair: (len(pair[0]), pair[0]))

        prefix = [(n, c) for n, c in table.items() if n.startswith(company_name)]
        inner = [
            (n, c)
            for n, c in table.items()
            if company_name in n and not n.startswith(company_name)
        ]
        return by_length(prefix) + by_length(inner)

    def find_corp_code(self, company_name: str) -> str | None:
        """회사명으로 8자리 고유번호를 찾는다. 전체 목록은 로컬에 캐시한다.

        후보가 여럿일 때 어느 것이 쓰였는지 알 수 없으므로, 리서처 경로(dart_search)는
        이 함수가 아니라 find_corp_candidates를 쓴다.
        """
        candidates = self.find_corp_candidates(company_name)
        return candidates[0][1] if candidates else None

    def _corp_code_table(self) -> dict[str, str]:
        if _CACHE.exists():
            try:
                return json.loads(_CACHE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # 캐시가 잘렸거나 읽을 수 없다 — 다시 받는다
                pass

        response = self._request("corpCode.xml")
        xml_bytes = self._read_zip_first_entry(response.content, "corpCode.xml")

        table: dict[str, str] = {}
        for item in ET.fromstring(xml_bytes).iter("list"):
            name = (item.findtext("corp_name") or "").strip()
            code = (item.findtext("corp_code") or "").strip()
            if name and code:
                table[name] = code

        self._write_cache(table)
        return table

    def _write_cache(self, table: dict[str, str]) -> None:
        """임시 파일에 쓰고 os.replace로 교체한다 — 중간에 죽어도 캐시가 손상되지 않는다."""
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, _CACHE)

    def list_disclosures(
        self, corp_code: str, begin: str, end: str, kind: str | None = None
    ) -> list[dict]:
        params = {
            "corp_code": corp_code,
            "bgn_de": begin,
            "end_de": end,
            "page_count": "100",
        }
        if kind:
            params["pblntf_ty"] = kind
        return self._get_json("list.json", **params).get("list", [])

    def fetch_document(self, rcept_no: str) -> str:
        """공시 원문(zip 안의 XML)을 텍스트로 반환한다."""
        response = self._request("document.xml", rcept_no=rcept_no)
        raw = self._read_zip_first_entry(response.content, "document.xml")
        return raw.decode("utf-8", errors="replace")


_shared: DartClient | None = None


def _shared_client() -> DartClient:
    """모듈 전역 싱글턴. dart_search가 호출될 때마다 새 커넥션 풀을 만들지 않는다."""
    global _shared
    if _shared is None:
        key = os.environ.get("DART_API_KEY")
        if not key:
            raise DartError("DART_API_KEY 환경변수가 설정되지 않았다")
        _shared = DartClient(api_key=key)
    return _shared


@beta_tool
def dart_search(company_name: str, keyword: str) -> str:
    """DART 공시에서 기업의 특정 주제 관련 내용을 찾는다.

    감사보고서 주석의 수주잔고·계약부채·무형자산·산업재산권, 기술성 평가 관련
    서류를 확인할 때 쓴다. 비상장 기업은 공시 의무가 없어 결과가 없을 수 있다.

    Args:
        company_name: 회사명. 정확한 법인명일수록 좋다.
        keyword: 찾고자 하는 주제 (예: "산업재산권", "수주잔고", "기술성 평가").
    """
    client = _shared_client()
    candidates = client.find_corp_candidates(company_name)
    if not candidates:
        return f"DART에서 '{company_name}'을(를) 찾지 못했다. 비상장이라 공시 의무가 없을 수 있다."

    corp_name, corp_code = candidates[0]
    if corp_name != company_name and len(candidates) > 1:
        # 어느 법인인지 우리가 몰래 고르지 않는다. 잘못된 법인의 공시는 tier 1로
        # 기록되고, 조회어만 되돌려주면 바꿔치기를 아무도 볼 수 없다.
        listing = "\n".join(
            f"- {name} (고유번호 {code})" for name, code in candidates[:10]
        )
        return (
            f"'{company_name}'과 정확히 일치하는 법인이 DART에 없고 후보가 "
            f"{len(candidates)}건이다. 어느 법인인지 확정한 뒤 정확한 법인명으로 다시 "
            f"조회하라. 지주회사·계열사를 대상 기업으로 오인하면 판정이 무의미해진다.\n"
            f"{listing}"
        )

    #: 조회어가 아니라 '실제로 매칭된 법인명'을 모든 반환 문자열에 담는다.
    matched = f"'{corp_name}'(고유번호 {corp_code})"
    if corp_name != company_name:
        matched += f" — 조회어 '{company_name}'의 부분 일치"

    rows = client.list_disclosures(corp_code, "20220101", "20261231")
    if not rows:
        return f"{matched}의 공시가 없다."

    hits: list[str] = []
    for row in rows[:20]:
        text = client.fetch_document(row["rcept_no"])
        if keyword not in text:
            continue
        index = text.index(keyword)
        excerpt = text[max(0, index - 400) : index + 400]
        hits.append(
            f"[{row['rcept_dt']}] {row['report_nm']} (접수번호 {row['rcept_no']})\n{excerpt}"
        )
        if len(hits) >= 5:
            break

    if not hits:
        return f"{matched}의 최근 공시 {len(rows)}건에서 '{keyword}'를 찾지 못했다."
    return f"{matched} 공시에서 '{keyword}' 검색 결과:\n\n" + "\n\n---\n\n".join(hits)
