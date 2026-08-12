from types import SimpleNamespace

import pytest
from pydantic import ValidationError

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

    def __init__(self, messages, tool_responses=None):
        self._messages = messages
        # 실제 러너는 방금 소비한 assistant 턴의 tool_use에 대한 user 메시지를
        # 돌려준다. 대역은 소비 순서대로 미리 정해둔 응답을 하나씩 내준다.
        self._tool_responses = list(tool_responses or [])
        self._consumed = 0

    def __iter__(self):
        self._consumed = 0
        return iter(self._messages)

    def generate_tool_call_response(self):
        # 실제 러너와 동일한 계약: 처리할 tool_use가 없으면 None.
        index, self._consumed = self._consumed, self._consumed + 1
        if index < len(self._tool_responses):
            return self._tool_responses[index]
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


# --- 조사 전문에 1차 출처가 실리는가 (Important 3) ---


def test_transcript_carries_tool_results_not_just_researcher_prose():
    """추출 단계는 `quote`가 "반드시 기록에 실제로 있는 원문"이길 요구한다.

    text 블록만 모으면 리서처가 '무엇을 찾았다고 말했는지'만 남고 1차 출처(DART
    발췌·웹 검색 결과)는 통째로 버려진다. 그러면 모델은 인용을 지어내거나 요약할
    수밖에 없고, source_tier도 리서처의 서술에만 의존하게 된다.
    """
    assistant = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="DART에서 산업재산권 주석을 찾았다"),
            SimpleNamespace(
                type="tool_use",
                id="tu_1",
                name="dart_search",
                input={"company_name": "테스트기업", "keyword": "산업재산권"},
            ),
        ],
        stop_reason="tool_use",
    )
    tool_result = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tu_1",
                "content": "[20250315] 사업보고서 (접수번호 20250315000001)\n등록 특허 12건 보유",
            }
        ],
    }
    client = FakeClient(
        runner=FakeRunner([assistant, _msg("정리하면 특허 12건이다")], [tool_result])
    )
    transcript = research_block(client, "B", "테스트기업", CAL)

    # 1차 출처 원문이 전문에 들어와야 한다
    assert "등록 특허 12건 보유" in transcript
    assert "20250315000001" in transcript
    # 리서처의 서술도 여전히 있어야 한다
    assert "정리하면 특허 12건이다" in transcript
    # 그리고 둘을 구분할 수 있어야 한다 — source_tier 판정이 이 구분에 걸려 있다
    assert "dart_search" in transcript or "DART" in transcript


def test_transcript_labels_web_search_results_distinctly_from_dart():
    """웹 검색 결과와 DART 발췌를 같은 덩어리로 뭉치면 등급 판정이 불가능해진다."""
    assistant = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="server_tool_use",
                id="srv_1",
                name="web_search",
                input={"query": "테스트기업 KOLAS 시험성적서"},
            ),
            SimpleNamespace(
                type="web_search_tool_result",
                tool_use_id="srv_1",
                content=[
                    SimpleNamespace(
                        type="web_search_result",
                        title="테스트기업, KOLAS 공인 시험성적서 취득",
                        url="https://news.example.com/a",
                        page_age="2025-04-01",
                    )
                ],
            ),
        ],
        stop_reason="end_turn",
    )
    client = FakeClient(runner=FakeRunner([assistant]))
    transcript = research_block(client, "A", "테스트기업", CAL)

    assert "https://news.example.com/a" in transcript
    assert "KOLAS 공인 시험성적서 취득" in transcript
    assert "웹 검색" in transcript


def test_transcript_excludes_the_research_prompt_itself():
    """조사 프롬프트(판정 기준 문구)가 전문에 섞이면 추출 모델이 그것을 근거로 오인한다."""
    client = FakeClient(runner=FakeRunner([_msg("조사 결과")]))
    transcript = research_block(client, "A", "테스트기업", CAL)
    assert "조사할 항목" not in transcript
    assert CAL.thresholds["A1_poc_reproducibility"] not in transcript


def test_unquotable_blocks_never_become_python_reprs_in_the_transcript():
    """전문은 추출 모델에게 '원문 기록'으로 제시된다. repr을 흘리면 인용할 수 없는 것을
    인용 가능한 것처럼 보이게 만든다."""
    assistant = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use", id="tu_1", name="dart_search", input={"k": "v"}
            )
        ],
        stop_reason="tool_use",
    )
    tool_result = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tu_1",
                "content": [
                    {"type": "text", "text": "진짜 원문"},
                    {"type": "image", "source": {"data": "AAAA"}},
                ],
            }
        ],
    }
    client = FakeClient(runner=FakeRunner([assistant], [tool_result]))
    transcript = research_block(client, "A", "테스트기업", CAL)

    assert "진짜 원문" in transcript
    assert "AAAA" not in transcript
    assert "{" not in transcript.split("진짜 원문")[1], "파이썬 repr이 전문에 샜다"


# --- 잘린 조사가 보이는가 (Important 6) ---


def test_iteration_exhaustion_is_recorded_in_notes():
    """반복 한도로 잘린 조사와 '찾아봤는데 없었다'는 전혀 다른 정보다."""
    notes: list[str] = []
    client = FakeClient(runner=FakeRunner([_msg("중간까지", stop_reason="tool_use")]))
    research_block(client, "A", "테스트기업", CAL, max_iterations=1, notes=notes)
    assert notes, "반복 한도 소진이 기록되지 않았다"
    assert any("A" in n for n in notes)


def test_restart_exhaustion_is_recorded_in_notes():
    notes: list[str] = []
    # 매번 pause_turn으로 끝나 재시작을 반복한다 — 재시작 한도까지 소진된다
    client = FakeClient(runner=FakeRunner([_msg("멈춤", stop_reason="pause_turn")]))
    research_block(client, "C", "테스트기업", CAL, notes=notes)
    assert notes, "재시작 한도 소진이 기록되지 않았다"


def test_iteration_budget_is_shared_across_restarts():
    """max_iterations가 재시작마다 새로 주어지면 실제 상한은 12가 아니라 36이 된다."""
    notes: list[str] = []
    client = FakeClient(runner=FakeRunner([_msg("멈춤", stop_reason="pause_turn")]))
    research_block(client, "A", "테스트기업", CAL, max_iterations=2, notes=notes)

    assert len(client.runner_calls) == 2, "예산은 재시작 전체에 걸쳐 나눠 쓴다"
    assert client.runner_calls[0]["max_iterations"] == 2
    assert client.runner_calls[1]["max_iterations"] == 1


def test_no_notes_when_research_completes_normally():
    notes: list[str] = []
    client = FakeClient(runner=FakeRunner([_msg("조사 완료")]))
    research_block(client, "A", "테스트기업", CAL, notes=notes)
    assert notes == []


# --- 추출 실패가 런을 죽이지 않는가 (Important 7) ---


class _FailingParseClient(FakeClient):
    """messages.parse가 앞의 `failures`번 호출에서 ValidationError를 던진다."""

    def __init__(self, failures: int, parsed=None):
        super().__init__(parsed=parsed)
        outer = self
        remaining = {"n": failures}

        class _Messages:
            def parse(self, **kwargs):
                outer.parse_calls.append(kwargs)
                if remaining["n"] > 0:
                    remaining["n"] -= 1
                    raise ValidationError.from_exception_data(
                        "EvidenceList",
                        [
                            {
                                "type": "less_than_equal",
                                "loc": ("items", 0, "source_tier"),
                                "input": 5,
                                "ctx": {"le": 4},
                            }
                        ],
                    )
                return SimpleNamespace(parsed_output=outer._parsed, stop_reason="end_turn")

        self.messages = _Messages()


def test_extraction_validation_error_is_retried_once():
    """조사 비용은 이미 다 치렀다. 스키마 위반 하나로 런을 죽이지 않는다."""
    expected = [
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MET",
            source_tier=2,
            quote="인용",
        )
    ]
    client = _FailingParseClient(failures=1, parsed=EvidenceList(items=expected))
    notes: list[str] = []
    assert extract_evidence(client, "A", "조사 전문", notes=notes) == expected
    assert len(client.parse_calls) == 2, "정확히 한 번 재시도한다"
    assert notes == [], "재시도가 성공했으면 결함으로 기록하지 않는다"


def test_extraction_degrades_to_empty_with_note_after_retry_fails():
    client = _FailingParseClient(failures=2)
    notes: list[str] = []
    assert extract_evidence(client, "B", "조사 전문", notes=notes) == []
    assert len(client.parse_calls) == 2, "무한 재시도하지 않는다"
    assert len(notes) == 1
    assert "B" in notes[0]


def test_run_block_threads_notes_from_both_stages():
    client = FakeClient(runner=FakeRunner([_msg("중간까지", stop_reason="tool_use")]))
    notes: list[str] = []
    run_block(client, "A", "테스트기업", CAL, notes=notes)
    assert notes, "research_block의 기록이 run_block을 통과해 전달돼야 한다"


def test_run_block_skips_extraction_when_transcript_is_empty():
    # 조사 전문이 비어 있으면(공백뿐이어도) 새로 추출을 호출하지 않는다
    client = FakeClient(runner=FakeRunner([_msg("   ")]))
    assert run_block(client, "A", "테스트기업", CAL) == []
    assert client.parse_calls == []
