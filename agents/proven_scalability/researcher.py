"""블록별 리서처. 조사(Tool Runner)와 추출(구조화 출력)을 분리한다.

조사 중에는 자유롭게 탐색하되, 경계에서 Evidence 스키마로 타입을 강제한다.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

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


#: 툴 이름 → 조사 전문에 붙일 출처 라벨. 추출 모델이 source_tier를 매기려면
#: DART 발췌인지 웹 검색 결과인지 리서처의 서술인지를 구분할 수 있어야 한다.
_TOOL_LABEL = {
    "dart_search": "DART 공시 원문 발췌 (1급 출처)",
    "patent_search": "특허 조회 결과",
    "web_search": "웹 검색 결과",
}


def _field(block, name, default=None):
    """블록은 SDK 모델 객체일 수도, 우리가 만든 파라미터 dict일 수도 있다."""
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def _has_pending_tool_use(content) -> bool:
    return any(_field(block, "type") == "tool_use" for block in content)


def _flatten_text(content) -> str:
    """tool_result의 content는 문자열이거나 블록 리스트다.

    알아보지 못한 블록은 **내용을 싣지 않는다**. str(block)으로 파이썬 repr을 흘려
    넣으면, "기록에 실제로 있는 원문만 인용하라"는 지시를 받은 추출 모델에게 원문처럼
    생긴 가짜 텍스트를 주는 꼴이다. 인용할 수 없는 것은 아예 없는 편이 낫다.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if _field(block, "type") == "text":
            parts.append(_field(block, "text", ""))
        else:
            # 종류만 밝히고 내용은 버린다 — 뭔가 있었다는 사실만 남긴다.
            kind = _field(block, "type") or "unknown"
            parts.append(f"(인용 불가 블록 생략: {kind})")
    return "\n".join(p for p in parts if p)


def _render_block(block, tool_names: dict[str, str]) -> str | None:
    """대화 블록 하나를 라벨 붙은 텍스트로 만든다. 실을 것이 없으면 None."""
    kind = _field(block, "type")

    if kind == "text":
        text = (_field(block, "text") or "").strip()
        return f"[리서처 서술]\n{text}" if text else None

    if kind in ("tool_use", "server_tool_use"):
        name = _field(block, "name", "tool")
        tool_id = _field(block, "id")
        if tool_id:
            tool_names[tool_id] = name
        arguments = _field(block, "input") or {}
        return f"[툴 호출: {name}] {json.dumps(arguments, ensure_ascii=False)}"

    if kind == "tool_result":
        name = tool_names.get(_field(block, "tool_use_id"), "tool")
        label = _TOOL_LABEL.get(name, f"{name} 결과")
        body = _flatten_text(_field(block, "content", "")).strip()
        return f"[{label}]\n{body}" if body else None

    if kind == "web_search_tool_result":
        results = _field(block, "content") or []
        if not isinstance(results, list):  # 에러 객체가 오는 경우
            return f"[웹 검색 결과: 오류] {_field(results, 'error_code', results)}"
        lines = []
        for item in results:
            title = _field(item, "title", "")
            url = _field(item, "url", "")
            age = _field(item, "page_age")
            lines.append(f"- {title} — {url}" + (f" ({age})" if age else ""))
        body = "\n".join(lines)
        return f"[{_TOOL_LABEL['web_search']}]\n{body}" if body else None

    return None  # thinking 등 조사 근거가 아닌 블록


def _build_transcript(messages: list) -> str:
    """대화 전체(assistant 서술 + 툴 결과 원문)를 추출 단계용 전문으로 만든다.

    text 블록만 모으면 1차 출처가 통째로 사라져, 추출 모델이 "기록에 실제로 있는
    원문"을 인용하라는 지시를 지킬 방법이 없어진다. source_tier도 리서처의 서술에만
    의존하게 되어 '자체 테스트만으로는 불인정' 규칙의 근거가 사라진다.

    messages[0]은 우리가 만든 조사 프롬프트다 — 판정 기준 문구가 전문에 섞이면
    추출 모델이 그것을 근거로 오인하므로 제외한다.
    """
    tool_names: dict[str, str] = {}
    parts: list[str] = []
    for message in messages[1:]:
        content = _field(message, "content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for block in content or []:
            rendered = _render_block(block, tool_names)
            if rendered:
                parts.append(rendered)
    return "\n\n".join(parts)


def research_block(
    client,
    block: Block,
    company: str,
    calibration: Calibration,
    max_iterations: int = 12,
    notes: list[str] | None = None,
) -> str:
    """1단계 — 툴을 써서 조사한다. 판정하지 않고 조사 전문을 문자열로 돌려준다.

    러너는 messages 파라미터를 자기 내부 사본으로 복사해 매 턴(assistant
    tool_use, user tool_result)을 그 사본에 쌓는다 — 밖에서는 보이지 않는다.
    pause_turn으로 재시작할 때 지금까지의 조사 내역(DART·KIPRIS·웹 검색 결과)을
    잃지 않으려면, 여기서 같은 대화를 로컬 `messages`에도 직접 미러링해야 한다.

    Args:
        max_iterations: 이 블록 조사 **전체**의 툴 호출 상한. 재시작에 걸쳐 나눠 쓴다 —
            재시작마다 새로 주면 실제 상한이 이름의 3배가 된다.
        notes: 조사가 잘렸을 때 사유를 append할 누적기. 결과의 research_notes로 흘러간다.
            잘린 조사와 '찾아봤지만 없었다'는 전혀 다른 정보다 (설계 §4).
    """
    notes = notes if notes is not None else []
    messages = [
        {"role": "user", "content": research_prompt(block, company, calibration)}
    ]

    remaining = max_iterations
    attempts = 0
    last = None

    while attempts < _MAX_RESTARTS:
        if remaining <= 0:
            notes.append(
                f"({block}) 블록: 툴 호출 한도 {max_iterations}회를 모두 쓰고 조사를 "
                "중단했다. 이 블록의 낮은 커버리지는 조사 결과가 아니라 중단의 결과일 수 있다."
            )
            break
        attempts += 1

        runner = client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=_MAX_TOKENS,
            tools=[dart_search, patent_search, WEB_SEARCH_TOOL],
            messages=messages,
            max_iterations=remaining,
        )
        last = None
        for message in runner:
            if message.stop_reason == "refusal":
                raise RefusalError(f"({block}) 블록 조사가 거부됐다")
            remaining -= 1

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

        if last is not None and last.stop_reason == "tool_use":
            # 러너가 반복 한도에 걸려 멈췄다 — 아직 부를 툴이 남아 있었다는 뜻이다.
            notes.append(
                f"({block}) 블록: 툴 호출 한도에 걸려 조사가 끝나기 전에 중단됐다. "
                "이 블록의 낮은 커버리지는 조사 결과가 아니라 중단의 결과일 수 있다."
            )
            break
        if last is None or last.stop_reason != "pause_turn":
            break
        # 로컬 messages에는 이미 paused 턴까지 전체 조사 내역이 미러링되어
        # 있다. 다음 루프가 이 messages로 새 러너를 만들어 이어서 조사한다.
    else:
        # while이 break 없이 끝났다 = 재시작 한도를 다 썼는데도 여전히 멈춘 상태다.
        if last is not None and last.stop_reason == "pause_turn":
            notes.append(
                f"({block}) 블록: 재시작 {_MAX_RESTARTS}회를 모두 쓰고도 조사가 "
                "pause 상태로 끝났다. 조사가 완결되지 않았다."
            )

    return _build_transcript(messages)


def extract_evidence(
    client, block: Block, transcript: str, notes: list[str] | None = None
) -> list[Evidence]:
    """2단계 — 조사 전문을 Evidence 스키마로 캐스팅한다. 툴 없음, 새 조사 없음.

    클라이언트 측 스키마 변환은 `ge=1, le=4` 같은 제약을 description으로 옮기므로
    API는 `source_tier: 5`를 막아주지 않는다. 막는 건 messages.parse 안의 pydantic이고,
    그 ValidationError를 그냥 두면 세 블록의 조사 비용을 다 치른 뒤 런 전체가 죽는다.
    한 번 재시도하고, 그래도 실패하면 이 블록만 빈 근거로 강등하고 기록을 남긴다.
    """
    notes = notes if notes is not None else []
    attempts = 2

    for attempt in range(1, attempts + 1):
        try:
            response = client.messages.parse(
                model=MODEL,
                max_tokens=_MAX_TOKENS,
                system=EXTRACTION_SYSTEM,
                messages=[
                    {"role": "user", "content": extraction_prompt(block, transcript)}
                ],
                output_format=EvidenceList,
            )
        except ValidationError as exc:
            if attempt < attempts:
                continue
            notes.append(
                f"({block}) 블록: 추출 결과가 Evidence 스키마 검증에 {attempts}회 연속 "
                f"실패해({exc.error_count()}건의 오류) 근거 없이 넘어갔다. 이 블록의 "
                "커버리지 하락은 조사 결과가 아니다."
            )
            return []

        if response.stop_reason == "refusal":
            raise RefusalError(f"({block}) 블록 추출이 거부됐다")
        parsed = response.parsed_output
        return list(parsed.items) if parsed else []

    return []  # 도달하지 않는다 (루프가 항상 return하거나 continue한다)


def run_block(
    client,
    block: Block,
    company: str,
    calibration: Calibration,
    notes: list[str] | None = None,
) -> list[Evidence]:
    notes = notes if notes is not None else []
    transcript = research_block(client, block, company, calibration, notes=notes)
    if not transcript.strip():
        return []
    return extract_evidence(client, block, transcript, notes=notes)
