import io
import zipfile

import httpx
import pytest

import agents.proven_scalability.tools.dart as dart
from agents.proven_scalability.tools.dart import DartClient, DartError, dart_search


def _client(handler) -> DartClient:
    transport = httpx.MockTransport(handler)
    return DartClient(api_key="test-key", http=httpx.Client(transport=transport))


def _zip_bytes(filename: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(filename, content)
    return buf.getvalue()


def test_list_disclosures_returns_rows():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "opendart.fss.or.kr" in str(request.url)
        return httpx.Response(
            200,
            json={
                "status": "000",
                "message": "정상",
                "list": [
                    {
                        "corp_name": "테스트",
                        "report_nm": "사업보고서",
                        "rcept_no": "20250315000001",
                        "rcept_dt": "20250315",
                    }
                ],
            },
        )

    rows = _client(handler).list_disclosures("00126380", "20240101", "20251231")
    assert len(rows) == 1
    assert rows[0]["rcept_no"] == "20250315000001"


def test_no_results_status_returns_empty_list_not_error():
    # DART는 조회 결과가 없을 때 status 013을 준다. 이건 에러가 아니다
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "013", "message": "조회된 데이터가 없습니다."})

    assert _client(handler).list_disclosures("00126380", "20240101", "20251231") == []


def test_api_error_status_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "020", "message": "요청 제한 초과"})

    with pytest.raises(DartError, match="020"):
        _client(handler).list_disclosures("00126380", "20240101", "20251231")


def test_api_key_never_appears_in_error_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "010", "message": "등록되지 않은 키"})

    with pytest.raises(DartError) as exc:
        _client(handler).list_disclosures("00126380", "20240101", "20251231")
    assert "test-key" not in str(exc.value)


def test_http_error_status_never_leaks_key_via_raise_for_status():
    # raise_for_status()의 예외 문자열에는 request.url이 담기고, url에는
    # crtfc_key가 들어 있다. DartClient는 그 예외를 절대 그대로 전파하면 안 된다.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized")

    with pytest.raises(DartError) as exc:
        _client(handler).list_disclosures("00126380", "20240101", "20251231")
    message = str(exc.value)
    assert "test-key" not in message
    assert "crtfc_key" not in message


def test_corp_code_table_parses_xml_and_caches(tmp_path, monkeypatch):
    cache_path = tmp_path / "corp_codes.json"
    monkeypatch.setattr(dart, "_CACHE", cache_path)

    xml = (
        b"<result>"
        b"<list><corp_code>00126380</corp_code><corp_name>\xec\x82\xbc\xec\x84\xb1\xec\xa0\x84\xec\x9e\x90</corp_name></list>"
        b"</result>"
    )
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))

    client = _client(handler)
    table = client._corp_code_table()
    assert table["삼성전자"] == "00126380"
    assert cache_path.exists()

    # 두 번째 호출은 캐시를 쓰고 네트워크를 다시 타지 않는다
    table2 = client._corp_code_table()
    assert table2 == table
    assert len(calls) == 1


def test_corp_code_table_falls_back_to_refetch_when_cache_corrupt(tmp_path, monkeypatch):
    cache_path = tmp_path / "corp_codes.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(dart, "_CACHE", cache_path)

    xml = b"<result><list><corp_code>00999999</corp_code><corp_name>test</corp_name></list></result>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))

    table = _client(handler)._corp_code_table()
    assert table["test"] == "00999999"


def test_fetch_document_extracts_zip_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_zip_bytes("doc.xml", "산업재산권 보유 현황".encode("utf-8")))

    text = _client(handler).fetch_document("20250315000001")
    assert "산업재산권" in text


def test_fetch_document_non_zip_response_raises_dart_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not a zip")

    with pytest.raises(DartError):
        _client(handler).fetch_document("20250315000001")


def test_dart_search_company_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")

    def handler(request: httpx.Request) -> httpx.Response:
        # corpCode.xml만 호출된다 — 빈 테이블
        return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", b"<result></result>"))

    monkeypatch.setattr(dart, "_shared", _client(handler))
    result = dart_search(company_name="존재하지않는회사", keyword="기술성")
    assert "찾지 못했다" in result


def test_dart_search_no_disclosures(monkeypatch, tmp_path):
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    xml = b"<result><list><corp_code>00126380</corp_code><corp_name>test</corp_name></list></result>"

    def handler(request: httpx.Request) -> httpx.Response:
        if "corpCode" in str(request.url):
            return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))
        return httpx.Response(200, json={"status": "013", "message": "조회된 데이터가 없습니다."})

    monkeypatch.setattr(dart, "_shared", _client(handler))
    result = dart_search(company_name="test", keyword="기술성")
    assert "공시가 없다" in result


def test_dart_search_keyword_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    xml = b"<result><list><corp_code>00126380</corp_code><corp_name>test</corp_name></list></result>"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "corpCode" in url:
            return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))
        if "list.json" in url:
            return httpx.Response(
                200,
                json={
                    "status": "000",
                    "message": "정상",
                    "list": [
                        {
                            "corp_name": "test",
                            "report_nm": "사업보고서",
                            "rcept_no": "20250315000001",
                            "rcept_dt": "20250315",
                        }
                    ],
                },
            )
        return httpx.Response(200, content=_zip_bytes("doc.xml", "무관한 내용".encode("utf-8")))

    monkeypatch.setattr(dart, "_shared", _client(handler))
    result = dart_search(company_name="test", keyword="산업재산권")
    assert "찾지 못했다" in result


def test_dart_search_successful_hit_builds_excerpt(monkeypatch, tmp_path):
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    xml = b"<result><list><corp_code>00126380</corp_code><corp_name>test</corp_name></list></result>"
    doc_text = ("배경 설명 " * 50) + "산업재산권 보유 현황" + (" 부연 설명" * 50)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "corpCode" in url:
            return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))
        if "list.json" in url:
            return httpx.Response(
                200,
                json={
                    "status": "000",
                    "message": "정상",
                    "list": [
                        {
                            "corp_name": "test",
                            "report_nm": "사업보고서",
                            "rcept_no": "20250315000001",
                            "rcept_dt": "20250315",
                        }
                    ],
                },
            )
        return httpx.Response(200, content=_zip_bytes("doc.xml", doc_text.encode("utf-8")))

    monkeypatch.setattr(dart, "_shared", _client(handler))
    result = dart_search(company_name="test", keyword="산업재산권")
    assert "산업재산권" in result
    assert "20250315" in result
    assert "사업보고서" in result
    assert "20250315000001" in result


# --- 법인 식별 (Important 5) ---
#
# 부분 문자열 첫 히트가 XML 문서 순서대로 이기면 '심텍' 조회가 '심텍홀딩스'로
# 풀릴 수 있다. 그 결과 나온 근거는 tier 1(공시)로 기록되는데, 조회어를 그대로
# 되돌려주기 때문에 모델도 심사역도 바꿔치기를 볼 수 없다.

_MULTI_XML = (
    "<result>"
    "<list><corp_code>00000001</corp_code><corp_name>심텍홀딩스</corp_name></list>"
    "<list><corp_code>00000002</corp_code><corp_name>심텍</corp_name></list>"
    "<list><corp_code>00000003</corp_code><corp_name>심텍글로벌</corp_name></list>"
    "</result>"
).encode("utf-8")


def _corp_table_handler(xml: bytes, list_json: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "corpCode" in url:
            return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))
        if "list.json" in url:
            return httpx.Response(
                200,
                json=list_json
                or {"status": "013", "message": "조회된 데이터가 없습니다."},
            )
        return httpx.Response(
            200, content=_zip_bytes("doc.xml", "내용".encode("utf-8"))
        )

    return handler


def test_exact_match_wins_over_longer_substring_match(tmp_path, monkeypatch):
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    client = _client(_corp_table_handler(_MULTI_XML))
    assert client.find_corp_code("심텍") == "00000002"


def test_ambiguous_name_returns_candidates_instead_of_guessing(tmp_path, monkeypatch):
    """정확 일치가 없고 후보가 여럿이면 하나를 몰래 고르지 않는다."""
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    xml = (
        "<result>"
        "<list><corp_code>00000001</corp_code><corp_name>심텍홀딩스</corp_name></list>"
        "<list><corp_code>00000003</corp_code><corp_name>심텍글로벌</corp_name></list>"
        "</result>"
    ).encode("utf-8")
    monkeypatch.setattr(dart, "_shared", _client(_corp_table_handler(xml)))

    result = dart_search(company_name="심텍", keyword="산업재산권")
    assert "심텍홀딩스" in result
    assert "심텍글로벌" in result
    # 조회를 진행하지 않고 확정을 요구해야 한다
    assert "공시가 없다" not in result


def test_single_substring_match_echoes_the_matched_legal_entity(tmp_path, monkeypatch):
    """후보가 하나뿐이어도 바꿔치기 사실 자체는 보여야 한다."""
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    xml = (
        "<result>"
        "<list><corp_code>00000001</corp_code><corp_name>심텍홀딩스</corp_name></list>"
        "</result>"
    ).encode("utf-8")
    monkeypatch.setattr(dart, "_shared", _client(_corp_table_handler(xml)))

    result = dart_search(company_name="심텍", keyword="산업재산권")
    assert "심텍홀딩스" in result, "조회어가 아니라 실제로 매칭된 법인명을 돌려줘야 한다"


def test_successful_hit_echoes_matched_corp_name(tmp_path, monkeypatch):
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")
    xml = b"<result><list><corp_code>00126380</corp_code><corp_name>test</corp_name></list></result>"
    rows = {
        "status": "000",
        "message": "정상",
        "list": [
            {
                "corp_name": "test",
                "report_nm": "사업보고서",
                "rcept_no": "20250315000001",
                "rcept_dt": "20250315",
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "corpCode" in url:
            return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", xml))
        if "list.json" in url:
            return httpx.Response(200, json=rows)
        return httpx.Response(
            200, content=_zip_bytes("doc.xml", "산업재산권 12건".encode("utf-8"))
        )

    monkeypatch.setattr(dart, "_shared", _client(handler))
    result = dart_search(company_name="test", keyword="산업재산권")
    assert "고유번호 00126380" in result
    assert "산업재산권 12건" in result


@pytest.mark.live
def test_live_dart_connection():
    """실제 DART 호출. `pytest -m live`로만 실행된다."""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DART_API_KEY")
    if not key:
        pytest.skip("DART_API_KEY 미설정")
    client = DartClient(api_key=key)
    code = client.find_corp_code("삼성전자")
    assert code is not None
    rows = client.list_disclosures(code, "20250101", "20251231")
    assert isinstance(rows, list)
