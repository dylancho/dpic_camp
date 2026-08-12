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


def research_block(
    client,
    block: Block,
    company: str,
    calibration: Calibration,
    max_iterations: int = 12,
) -> str:
    """1단계 — 툴을 써서 조사한다. 판정하지 않고 조사 전문을 문자열로 돌려준다."""
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
            last = message
            if message.stop_reason == "pause_turn":
                # 서버툴이 턴 중간에 멈췄다. 실제 러너는 이 지점에서 더 내놓을
                # 메시지가 없으므로(다음 tool_use가 없어 이터레이션이 끝난다),
                # 여기서 더 소비하지 않고 재시작 절차로 넘어간다.
                break

        if last is None or last.stop_reason != "pause_turn":
            break
        # Tool Runner는 pause_turn을 자동 재개하지 않는다. paused assistant
        # 턴을 messages에 이어붙여, 다음 루프에서 새 러너로 재시작한다.
        messages.append({"role": "assistant", "content": last.content})

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
