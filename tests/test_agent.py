import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.proven_scalability import agent
from agents.proven_scalability.agent import evaluate
from tests.fixtures.evidence import ev

#: 우연한 부분 문자열 일치가 불가능할 만큼 길고, 진짜 키처럼 보이는(그럴듯한 접두어 +
#: 무작위스러운 몸통) 값이어야 한다 — 값을 자르거나 패턴 매칭으로 일부만 가리는 회귀도 잡기 위해.
_SENTINEL_DART_KEY = "dart-live-9f3ac71b2e6d4480a5f9c1d7e8b0429f"


def _write_evidence(tmp_path: Path, items: list[dict]) -> Path:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return path


def _item(criterion_id: str, status: str = "MET", tier: int = 1) -> dict:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "source_tier": tier,
        "source_url": "https://example.com/doc",
        "quote": f"{criterion_id} 관련 인용",
    }


# --- 증거 파일 경로 ---


def test_evaluate_without_any_evidence_input_notes_that_nothing_was_provided():
    result = evaluate("테스트기업", archetype="materials", dart_client=object())

    assert result.evidence == []
    assert any("증거가 하나도 입력되지 않았다" in note for note in result.research_notes)


def test_evaluate_loads_and_scores_evidence_from_file(tmp_path):
    path = _write_evidence(
        tmp_path,
        [
            _item("A1_poc_reproducibility"),
            _item("A2_third_party_validation"),
            _item("B1_exchange_tech_grade"),
            _item("B2_registered_patents"),
            _item("C1_capacity_plan"),
        ],
    )

    result = evaluate(
        "테스트기업", archetype="materials", evidence_path=path, dart_client=object()
    )

    assert result.verdict == "PASS"
    assert result.block_scores.a == 10  # A 2개 충족
    assert result.block_scores.b == 5  # B 2개 충족
    assert result.block_scores.c == 2  # C 1개 충족
    assert result.score == 17
    assert len(result.evidence) == 5
    assert not any("증거가 하나도 입력되지 않았다" in n for n in result.research_notes)


def test_evaluate_carries_schema_violation_warnings_from_evidence_file(tmp_path):
    """스키마 위반 항목이 조용히 사라지지 않고 research_notes에 남아야 한다."""
    bad_item = {**_item("A1_poc_reproducibility"), "source_tier": 9}
    path = _write_evidence(tmp_path, [bad_item])

    result = evaluate(
        "테스트기업", archetype="materials", evidence_path=path, dart_client=object()
    )

    assert result.evidence == []
    assert any("스키마 위반" in note for note in result.research_notes)


def test_evaluate_without_archetype_marks_uncalibrated():
    result = evaluate("테스트기업", dart_client=object())

    assert result.calibration.archetype_injected is False
    assert result.calibration.archetype == "uncalibrated"
    assert result.verdict == "INSUFFICIENT_EVIDENCE"
    assert result.gate_failed == ["A", "B"]


def test_evaluate_bypasses_env_check_when_dart_client_is_given():
    """대역 dart_client를 넘기면 DART_API_KEY가 없어도 죽지 않는다."""
    with patch.object(agent, "_ensure_env_loaded") as mock_ensure:
        evaluate("테스트기업", dart_client=object())
    mock_ensure.assert_not_called()


def test_evaluate_checks_env_when_dart_client_is_not_given():
    with patch.object(agent, "_ensure_env_loaded") as mock_ensure:
        evaluate("테스트기업")
    mock_ensure.assert_called_once()


# --- 자격 증명 점검 (_ensure_env_loaded) ---
#
# 실제 .env를 절대 읽지 않도록 _ENV_PATH를 존재하지 않는 경로로 바꿔치기한다.
# load_dotenv()는 파일이 없으면 조용히 아무 것도 하지 않으므로, 여기서 monkeypatch로
# 세팅한 os.environ 값이 그대로 유지된다.


@pytest.fixture
def _no_real_dotenv(monkeypatch, tmp_path):
    """존재하지 않는 경로로 바꿔치기해 진짜 .env를 절대 건드리지 않는다."""
    monkeypatch.setattr(agent, "_ENV_PATH", tmp_path / "이런파일없음.env")


def test_ensure_env_loaded_names_missing_dart_key(monkeypatch, _no_real_dotenv):
    monkeypatch.delenv("DART_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    assert "DART_API_KEY" in str(exc_info.value)


def test_ensure_env_loaded_error_never_leaks_the_key_value(monkeypatch, _no_real_dotenv):
    """메시지는 없는 변수의 '이름'만 말해야 한다 — 다른 값이 실려 있어도 새면 안 된다."""
    monkeypatch.delenv("DART_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    message = str(exc_info.value)
    assert _SENTINEL_DART_KEY not in message
    assert "crtfc_key" not in message


def test_ensure_env_loaded_passes_when_dart_key_present(monkeypatch, _no_real_dotenv):
    monkeypatch.setenv("DART_API_KEY", _SENTINEL_DART_KEY)
    agent._ensure_env_loaded()  # 예외 없이 통과해야 한다


def test_anthropic_api_key_is_no_longer_required(monkeypatch, _no_real_dotenv):
    """LLM 층이 빠졌으므로 ANTHROPIC_API_KEY의 유무는 더 이상 문제되지 않는다."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DART_API_KEY", _SENTINEL_DART_KEY)

    agent._ensure_env_loaded()  # 예외 없이 통과해야 한다


def test_env_path_resolves_to_repo_root_not_cwd():
    """load_dotenv()를 인자 없이 부르면 CWD에서 위로 탐색한다 — 그 회귀를 잡는다."""
    expected = Path(agent.__file__).resolve().parents[2] / ".env"
    assert agent._ENV_PATH == expected
