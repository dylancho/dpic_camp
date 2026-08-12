"""KIPRIS 특허 조회 — 인터페이스만 정의되어 있다.

API 키를 확보하지 못했다. 키가 생기면 `patent_search` 본문을 실제 조회로 교체하고
`KiprisClient`를 이 파일에 추가한다. 그때까지 등록 특허 건수와 청구항 구조는
공개 소스로 판정할 수 없으므로, 리서처에게 '확인 불가'임을 명시적으로 알린다.
"""

from __future__ import annotations

from anthropic import beta_tool

_UNAVAILABLE = (
    "KIPRIS API 키가 확보되지 않아 특허 등록 건수와 청구항 구조를 조회할 수 없다. "
    "이 항목은 '확인 불가(UNVERIFIABLE)'로 기록하고 실사 질문으로 넘길 것. "
    "다만 DART 감사보고서의 무형자산·산업재산권 주석이나 웹 검색으로 "
    "간접 근거를 찾을 수 있다면 그것으로 기록해도 된다."
)


class KiprisUnavailable(Exception):
    """KIPRIS 키가 없거나 조회에 실패했을 때."""


@beta_tool
def patent_search(applicant: str) -> str:
    """출원인 이름으로 등록 특허를 조회한다.

    Args:
        applicant: 출원인(법인) 이름.
    """
    return _UNAVAILABLE
