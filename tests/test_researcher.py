from types import SimpleNamespace

import pytest

from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.researcher import (
    MODEL,
    EvidenceList,
    RefusalError,
    extract_evidence,
    research_block,
    run_block,
)
from agents.proven_scalability.schema import Evidence

CAL = resolve_thresholds("materials", None)


def _msg(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason
    )


class FakeRunner:
    """실제 BetaToolRunner에는 push_messages가 없다 — append_messages만 있다.
    이 대역도 그 사실을 흉내내지 않는 메서드는 두지 않는다.
    """

    def __init__(self, messages):
        self._messages = messages

    def __iter__(self):
        return iter(self._messages)

    def generate_tool_call_response(self):
        # 대역 메시지들은 tool_use 블록이 없으므로 항상 None을 돌려준다
        # (실제 러너와 동일한 계약: 처리할 tool_use가 없으면 None).
        return None


class FakeClient:
    """tool_runner와 messages.parse만 흉내낸다."""

    def __init__(self, runner=None, parsed=None, parse_stop_reason="end_turn"):
        self._runner = runner
        self._parsed = parsed
        self.parse_calls = []
        self.runner_calls = []
        outer = self

        class _Messages:
            def parse(self, **kwargs):
                outer.parse_calls.append(kwargs)
                return SimpleNamespace(
                    parsed_output=outer._parsed, stop_reason=parse_stop_reason
                )

        class _BetaMessages:
            def tool_runner(self, **kwargs):
                # messages는 research_block이 계속 mutate하는 공유 리스트다.
                # 나중에 두 번째 호출과 구분해서 검사할 수 있도록 호출 시점의
                # 스냅샷을 남긴다.
                snapshot = dict(kwargs)
                if "messages" in snapshot:
                    snapshot["messages"] = list(snapshot["messages"])
                outer.runner_calls.append(snapshot)
                return outer._runner

        self.messages = _Messages()
        self.beta = SimpleNamespace(messages=_BetaMessages())


def test_research_block_uses_opus_5_and_no_thinking_param():
    client = FakeClient(runner=FakeRunner([_msg("조사 결과")]))
    research_block(client, "A", "테스트기업", CAL)
    call = client.runner_calls[0]
    assert call["model"] == MODEL == "claude-opus-5"
    assert "thinking" not in call
    assert "temperature" not in call


def test_research_block_concatenates_text_across_messages():
    client = FakeClient(runner=FakeRunner([_msg("첫 번째"), _msg("두 번째")]))
    transcript = research_block(client, "A", "테스트기업", CAL)
    assert "첫 번째" in transcript
    assert "두 번째" in transcript


def test_research_block_resumes_on_pause_turn():
    # 실제 SDK의 러너에는 push_messages가 없다 (append_messages만 있다) —
    # 재개 메커니즘은 messages에 paused assistant 턴을 append한 뒤
    # 새 러너를 처음부터 구성하는 것이다. 두 번째 tool_runner() 호출의
    # messages 인자가 그 턴으로 끝나는지 확인한다.
    paused = _msg("중간까지", stop_reason="pause_turn")
    runner = FakeRunner([paused, _msg("마무리")])
    client = FakeClient(runner=runner)
    research_block(client, "A", "테스트기업", CAL)

    assert len(client.runner_calls) >= 2, "pause_turn이면 새 러너로 재시작해야 한다"
    # 첫 번째 호출의 스냅샷은 messages가 이후에 mutate돼도 영향받지 않는다 —
    # 두 호출을 서로 다른 시점으로 독립적으로 검사할 수 있다.
    first_messages = client.runner_calls[0]["messages"]
    assert len(first_messages) == 1, "첫 호출은 원본 조사 프롬프트만 가지고 있어야 한다"

    resumed_messages = client.runner_calls[1]["messages"]
    assert resumed_messages[-1] == {"role": "assistant", "content": paused.content}
    # 재시작은 처음부터가 아니라, paused 턴까지 미러링된 전체 조사 내역을
    # 이어받는다 — 그래서 이전 대화(원본 프롬프트)가 여전히 남아 있다.
    assert resumed_messages[0] == first_messages[0]


def test_research_block_raises_on_refusal():
    client = FakeClient(runner=FakeRunner([_msg("", stop_reason="refusal")]))
    with pytest.raises(RefusalError):
        research_block(client, "A", "테스트기업", CAL)


def test_extract_evidence_returns_typed_objects():
    expected = [
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MET",
            source_tier=2,
            source_url="https://example.com",
            quote="인용",
        )
    ]
    client = FakeClient(parsed=EvidenceList(items=expected))
    assert extract_evidence(client, "A", "조사 전문") == expected


def test_extract_evidence_requests_structured_output():
    client = FakeClient(parsed=EvidenceList(items=[]))
    extract_evidence(client, "A", "조사 전문")
    assert client.parse_calls[0]["output_format"] is EvidenceList


def test_extract_evidence_passes_no_tools():
    # 추출 단계는 새로 조사하지 않는다
    client = FakeClient(parsed=EvidenceList(items=[]))
    extract_evidence(client, "A", "조사 전문")
    assert "tools" not in client.parse_calls[0]


def test_extract_evidence_raises_on_refusal():
    client = FakeClient(parsed=None, parse_stop_reason="refusal")
    with pytest.raises(RefusalError):
        extract_evidence(client, "A", "조사 전문")


def test_extract_evidence_returns_empty_when_parsed_output_is_none():
    # output_format을 지정해도 parsed_output이 비어있을 수 있다 (예: 텍스트
    # 블록에 파싱된 결과가 실리지 않은 경우). None을 그대로 흘려보내지 않는다.
    client = FakeClient(parsed=None, parse_stop_reason="end_turn")
    assert extract_evidence(client, "A", "조사 전문") == []


def test_run_block_extracts_when_research_finds_something():
    expected = [
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MET",
            source_tier=2,
            quote="인용",
        )
    ]
    client = FakeClient(
        runner=FakeRunner([_msg("조사 결과 있음")]),
        parsed=EvidenceList(items=expected),
    )
    assert run_block(client, "A", "테스트기업", CAL) == expected
    assert len(client.parse_calls) == 1


def test_run_block_skips_extraction_when_transcript_is_empty():
    # 조사 전문이 비어 있으면(공백뿐이어도) 새로 추출을 호출하지 않는다
    client = FakeClient(runner=FakeRunner([_msg("   ")]))
    assert run_block(client, "A", "테스트기업", CAL) == []
    assert client.parse_calls == []
