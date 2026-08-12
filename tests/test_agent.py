from pathlib import Path
from unittest.mock import patch

import pytest

from agents.proven_scalability import agent
from agents.proven_scalability.agent import evaluate
from tests.fixtures.evidence import ev

_SENTINEL_DART_KEY = "sentinel-dart-key-should-never-appear-in-error"
_SENTINEL_ANTHROPIC_KEY = "sentinel-anthropic-key-should-never-appear-in-error"


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

    assert result.calibration.injected is False
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


def test_ensure_env_loaded_raises_when_anthropic_key_missing(monkeypatch, _no_real_dotenv):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DART_API_KEY", _SENTINEL_DART_KEY)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


def test_ensure_env_loaded_raises_when_dart_key_missing(monkeypatch, _no_real_dotenv):
    monkeypatch.setenv("ANTHROPIC_API_KEY", _SENTINEL_ANTHROPIC_KEY)
    monkeypatch.delenv("DART_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    assert "DART_API_KEY" in str(exc_info.value)


def test_ensure_env_loaded_error_never_leaks_secret_values(monkeypatch, _no_real_dotenv):
    """이름은 말해도 되지만 값은 절대 안 된다 — 두 키 다 없을 때도 확인한다."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DART_API_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        agent._ensure_env_loaded()

    message = str(exc_info.value)
    assert _SENTINEL_ANTHROPIC_KEY not in message
    assert _SENTINEL_DART_KEY not in message
    assert "crtfc_key" not in message


def test_env_path_resolves_to_repo_root_not_cwd():
    """load_dotenv()를 인자 없이 부르면 CWD에서 위로 탐색한다 — 그 회귀를 잡는다."""
    expected = Path(agent.__file__).resolve().parents[2] / ".env"
    assert agent._ENV_PATH == expected
