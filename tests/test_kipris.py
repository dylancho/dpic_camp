from agents.proven_scalability.tools import kipris
from agents.proven_scalability.tools.web import WEB_SEARCH_TOOL


def test_patent_search_reports_unavailability_explicitly():
    result = kipris.patent_search(applicant="테스트기업")
    assert "KIPRIS" in result
    # 리서처가 UNVERIFIABLE로 기록하도록 유도하는 문구가 있어야 한다
    assert "확인" in result


def test_patent_search_does_not_claim_zero_patents():
    # "특허 0건"으로 오해될 문구가 있으면 NOT_MET으로 잘못 기록된다
    result = kipris.patent_search(applicant="테스트기업")
    assert "0건" not in result
    assert "없습니다" not in result


def test_web_search_tool_uses_current_type():
    assert WEB_SEARCH_TOOL["type"] == "web_search_20260209"
    assert WEB_SEARCH_TOOL["name"] == "web_search"
