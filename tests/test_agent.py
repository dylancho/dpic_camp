from pathlib import Path
from unittest.mock import patch

import pytest

from agents.proven_scalability import agent
from agents.proven_scalability.agent import evaluate
from tests.fixtures.evidence import ev

#: 우연한 부분 문자열 일치가 불가능할 만큼 길고, 진짜 키처럼 보이는(그럴듯한 접두어 +
#: 무작위스러운 몸통) 값이어야 한다 — 값을 자르거나 패턴 매칭으로 일부만 가리는 회귀도 잡기 위해.
_SENTINEL_DART_KEY = "dart-live-9f3ac71b2e6d4480a5f9c1d7e8b0429f"
_SENTINEL_ANTHROPIC_KEY = "sk-ant-api03-Qh7mZ2xL9vR4tK8wN1pS6yF3dC5bA0eJ"


def test_evaluate_runs_all_three_blocks():
    calls = []

    def fake_run_block(client, block, company, calibration):
        calls.append(block)
        return [ev("A1_poc_reproducibility")] if block == "A" else []

    with patch("agents.proven_scalability.agent.run_block", fake_run_block):
        evaluate("테스트기업", archetype="materials", client=object())

    assert calls == ["A", "B", "C"]


def test_evaluate_merges_evidence_and_scores():
    per_block = {
        "A": [ev("A1_poc_reproducibility"), ev("A2_third_party_validation")],
        "B": [ev("B1_exchange_tech_grade"), ev("B2_registered_patents")],
        "C": [ev("C1_capacity_plan")],
    }

    with patch(
        "agents.proven_scalability.agent.run_block",
        lambda client, block, company, cal: per_block[block],
    ):
        result = evaluate("테스트기업", archetype="materials", client=object())

    assert result.verdict == "PASS"
    assert result.block_scores.a == 10  # A 2개 충족
    assert result.block_scores.b == 5  # B 2개 충족
    assert result.block_scores.c == 2  # C 1개 충족
    assert result.score == 17
    assert len(result.evidence) == 5


def test_evaluate_without_archetype_marks_uncalibrated():
    with patch(
        "agents.proven_scalability.agent.run_block", lambda *a, **k: []
    ):
        result = evaluate("테스트기업", client=object())

    assert result.calibration.archetype_injected is False
    assert result.calibration.archetype == "uncalibrated"
    assert result.verdict == "INSUFFICIENT_EVIDENCE"
    assert result.gate_failed == ["A", "B"]


# --- 자격 증명 점검 (_ensure_env_loaded) ---
#
# 실제 .env를 절대 읽지 않도록 _ENV_PATH를 존재하지 않는 경로로 바꿔치기한다.
# load_dotenv()는 파일이 없으면 조용히 아무 것도 하지 않으므로, 여기서 monkeypatch로
# 세팅한 os.environ 값이 그대로 유지된다.


@pytest.fixture
def _no_real_dotenv(monkeypatch, tmp_path):
    """존재하지 않는 경로로 바꿔치기해 진짜 .env를 절대 건드리지 않는다."""
    monkeypatch.setattr(agent, "_ENV_PATH", tmp_path / "이런파일없음.env")


def test_ensure_env_loaded_names_missing_anthropic_key_without_leaking_present_dart_value(
    monkeypatch, _no_real_dotenv
):
    """DART_API_KEY는 실재하는 값을 들고 있고, ANTHROPIC_API_KEY만 없다.

    메시지는 없는 쪽의 '이름'은 말해야 하고, 있는 쪽의 '값'은 절대 담으면 안 된다.
    두 절반을 한 케이스에서 같이 확인해야 한다 — 따로 보면 각각 공허하게 통과한다.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DART_API_KEY", _SENTINEL_DART_KEY)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    message = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in message
    assert _SENTINEL_DART_KEY not in message


def test_ensure_env_loaded_names_missing_dart_key_without_leaking_present_anthropic_value(
    monkeypatch, _no_real_dotenv
):
    """거울상 케이스 — ANTHROPIC_API_KEY는 실재하는 값을 들고 있고, DART_API_KEY만 없다."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", _SENTINEL_ANTHROPIC_KEY)
    monkeypatch.delenv("DART_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    message = str(exc_info.value)
    assert "DART_API_KEY" in message
    assert _SENTINEL_ANTHROPIC_KEY not in message


def test_ensure_env_loaded_error_never_leaks_secret_values_when_both_missing(
    monkeypatch, _no_real_dotenv
):
    """둘 다 없을 때도 (당연히 아무 값도 새지 않지만) crtfc_key 같은 내부 파라미터명이
    실수로 섞여 들어가지 않는지 확인한다."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DART_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    message = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in message
    assert "DART_API_KEY" in message
    assert "crtfc_key" not in message


def test_env_path_resolves_to_repo_root_not_cwd():
    """load_dotenv()를 인자 없이 부르면 CWD에서 위로 탐색한다 — 그 회귀를 잡는다."""
    expected = Path(agent.__file__).resolve().parents[2] / ".env"
    assert agent._ENV_PATH == expected
