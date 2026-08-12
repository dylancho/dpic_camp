"""블록별 리서처. 조사(Tool Runner)와 추출(구조화 출력)을 분리한다.

조사 중에는 자유롭게 탐색하되, 경계에서 Evidence 스키마로 타입을 강제한다.
"""

from __future__ import annotations

from pydantic import BaseModel

from agents.proven_scalability.prompts import (
    EXTRACTION_SYSTEM,
    extraction_prompt,
    research_prompt,
)
from agents.proven_scalability.schema import Block, Calibration, Evidence
from agents.proven_scalability.tools.dart import dart_search
from agents.proven_scalability.tools.kipris import patent_search
from agents.proven_scalability.tools.web import WEB_SEARCH_TOOL

MODEL = "claude-opus-5"
_MAX_TOKENS = 16000
_MAX_RESTARTS = 3


class RefusalError(Exception):
    """모델이 요청을 거부했을 때 (stop_reason == "refusal")."""


class EvidenceList(BaseModel):
    """구조화 출력용 래퍼. 최상위가 객체여야 하므로 리스트를 감싼다."""

    items: list[Evidence]


def _text_of(message) -> str:
    return "\n".join(b.text for b in message.content if b.type == "text")


def _has_pending_tool_use(content) -> bool:
    return any(getattr(block, "type", None) == "tool_use" for block in content)


def research_block(
    client,
    block: Block,
    company: str,
    calibration: Calibration,
    max_iterations: int = 12,
) -> str:
    """1단계 — 툴을 써서 조사한다. 판정하지 않고 조사 전문을 문자열로 돌려준다.

    러너는 messages 파라미터를 자기 내부 사본으로 복사해 매 턴(assistant
    tool_use, user tool_result)을 그 사본에 쌓는다 — 밖에서는 보이지 않는다.
    pause_turn으로 재시작할 때 지금까지의 조사 내역(DART·KIPRIS·웹 검색 결과)을
    잃지 않으려면, 여기서 같은 대화를 로컬 `messages`에도 직접 미러링해야 한다.
    """
    messages = [
        {"role": "user", "content": research_prompt(block, company, calibration)}
    ]
    parts: list[str] = []

    for _ in range(_MAX_RESTARTS):
        runner = client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=_MAX_TOKENS,
            tools=[dart_search, patent_search, WEB_SEARCH_TOOL],
            messages=messages,
            max_iterations=max_iterations,
        )
        last = None
        for message in runner:
            if message.stop_reason == "refusal":
                raise RefusalError(f"({block}) 블록 조사가 거부됐다")
            parts.append(_text_of(message))

            # 러너가 쌓는 내부 대화를 로컬에도 그대로 미러링한다.
            messages.append({"role": "assistant", "content": message.content})
            # generate_tool_call_response()는 캐시된다 — 여기서 불러도 툴이
            # 다시 실행되지 않는다. tool_use가 없으면 None을 돌려준다.
            tool_response = runner.generate_tool_call_response()
            if tool_response is not None:
                messages.append(tool_response)

            last = message
            if message.stop_reason == "pause_turn" and not _has_pending_tool_use(
                message.content
            ):
                # 서버툴이 턴 중간에 멈췄고 응답을 기다리는 tool_use가 없다.
                # 실제 러너는 이 지점에서 더 내놓을 메시지가 없으므로(다음
                # 이터레이션에 넘길 tool_use가 없어 __run__이 끝난다), 여기서도
                # 더 소비하지 않고 재시작 절차로 넘어간다. tool_use가 남아
                # 있다면 러너가 아직 처리 중이므로 그대로 계속 소비한다.
                break

        if last is None or last.stop_reason != "pause_turn":
            break
        # 로컬 messages에는 이미 paused 턴까지 전체 조사 내역이 미러링되어
        # 있다. 다음 루프가 이 messages로 새 러너를 만들어 이어서 조사한다.

    return "\n\n".join(p for p in parts if p.strip())


def extract_evidence(client, block: Block, transcript: str) -> list[Evidence]:
    """2단계 — 조사 전문을 Evidence 스키마로 캐스팅한다. 툴 없음, 새 조사 없음."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=_MAX_TOKENS,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": extraction_prompt(block, transcript)}],
        output_format=EvidenceList,
    )
    if response.stop_reason == "refusal":
        raise RefusalError(f"({block}) 블록 추출이 거부됐다")
    parsed = response.parsed_output
    return list(parsed.items) if parsed else []


def run_block(
    client, block: Block, company: str, calibration: Calibration
) -> list[Evidence]:
    transcript = research_block(client, block, company, calibration)
    if not transcript.strip():
        return []
    return extract_evidence(client, block, transcript)
