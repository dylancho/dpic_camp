"""웹 검색 서버 툴 정의.

Anthropic 서버에서 실행되므로 클라이언트 구현이 없다. Tool Runner의 tools 배열에
그대로 넣으면 된다. `_20260209` 버전은 동적 필터링이 내장되어 있으므로
code_execution 툴을 따로 선언하지 않는다.
"""

from __future__ import annotations

WEB_SEARCH_TOOL: dict = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 12,
}
