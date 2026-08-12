import httpx
import pytest

from agents.proven_scalability.tools.dart import DartClient, DartError


def _client(handler) -> DartClient:
    transport = httpx.MockTransport(handler)
    return DartClient(api_key="test-key", http=httpx.Client(transport=transport))


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
