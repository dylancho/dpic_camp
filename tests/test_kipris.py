from agents.proven_scalability.tools import kipris
from agents.proven_scalability.tools.web import WEB_SEARCH_TOOL


def test_patent_search_reports_unavailability_explicitly():
    result = kipris.patent_search(applicant="테스트기업")
    assert "KIPRIS" in result
    # 리서처가 UNVERIFIABLE로 기록하도록 유도하는 문구가 있어야 한다
    assert "확인" in result


def test_patent_search_does_not_claim_zero_patents():
    import re

    # Why this guard exists: incorrect wording that implies zero patents
    # causes the researcher to record B2_registered_patents as NOT_MET,
    # which falsely asserts the company has no patents and wrongly costs it
    # 해자 points. Only 확인 불가 (UNVERIFIABLE) is correct.

    result = kipris.patent_search(applicant="테스트기업")

    # Literal substrings that directly assert zero count
    # (these document the specific cases that motivated the guard)
    assert "0건" not in result
    assert "없습니다" not in result

    # Broader pattern check for Korean absence/zero-count assertions
    # that would be misinterpreted as "company has zero patents"
    zero_patent_patterns = [
        r"0\s*[건개]",  # 0건, 0개, 0 건, 0 개
        r"미보유",  # not held/owned
        r"해당\s*없음",  # not applicable
        r"존재하지\s*않",  # does not exist
        r"보유하지\s*않",  # do not own/hold
    ]

    for pattern in zero_patent_patterns:
        assert not re.search(pattern, result), f"Pattern '{pattern}' found in: {result}"


def test_web_search_tool_uses_current_type():
    assert WEB_SEARCH_TOOL["type"] == "web_search_20260209"
    assert WEB_SEARCH_TOOL["name"] == "web_search"
