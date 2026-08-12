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

    def find_corp_code(self, company_name: str) -> str | None:
        """회사명으로 8자리 고유번호를 찾는다. 전체 목록은 로컬에 캐시한다."""
        table = self._corp_code_table()
        exact = table.get(company_name)
        if exact:
            return exact
        for name, code in table.items():
            if company_name in name:
                return code
        return None

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
    corp_code = client.find_corp_code(company_name)
    if corp_code is None:
        return f"DART에서 '{company_name}'을(를) 찾지 못했다. 비상장이라 공시 의무가 없을 수 있다."

    rows = client.list_disclosures(corp_code, "20220101", "20261231")
    if not rows:
        return f"'{company_name}'(고유번호 {corp_code})의 공시가 없다."

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
        return f"'{company_name}'의 최근 공시 {len(rows)}건에서 '{keyword}'를 찾지 못했다."
    return "\n\n---\n\n".join(hits)
