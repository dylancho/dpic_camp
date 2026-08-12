from unittest.mock import patch

from agents.proven_scalability.agent import evaluate
from tests.fixtures.evidence import ev


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
