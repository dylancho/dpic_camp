"""CLI 표면 테스트.

evaluate를 대역으로 바꿔 네트워크를 절대 타지 않는다. CLI는 결과를 '보여주는' 층이라
로직이 없어 보이지만, 여기서 잘못 표시하면 잘못된 판단 근거가 사람에게 그대로 간다 —
(미보정) 라벨과 조사 결함 기록이 정확히 그런 것들이다.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.proven_scalability import __main__ as cli
from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.evidence_io import EvidenceFileError
from agents.proven_scalability.scoring import score
from tests.fixtures.evidence import ev


def _run(argv: list[str], result) -> str:
    """main()을 돌리고 표준출력을 돌려준다. evaluate는 부르지 않는다."""
    with patch.object(cli, "evaluate", lambda *a, **k: result):
        with patch("sys.argv", ["proven-scalability", *argv]):
            assert cli.main() == 0


@pytest.fixture
def capture(capsys):
    def run(argv: list[str], result) -> str:
        _run(argv, result)
        return capsys.readouterr().out

    return run


def _result(archetype=None, notes=None, evidence=None):
    return score(
        evidence or [],
        resolve_thresholds(archetype, None),
        research_notes=notes,
    )


# --- 보정 라벨 ---


def test_uncalibrated_label_appears_only_without_an_archetype(capture):
    out = capture(["--company", "테스트기업"], _result(archetype=None))
    assert "(미보정)" in out
    assert "uncalibrated" in out


def test_archetype_run_is_not_labelled_uncalibrated(capture):
    """--thresholds 플래그가 없으므로 모든 --archetype 실행이 이 경로다.

    라벨을 thresholds_injected로 게이트하면 여기서 (미보정)이 뜬다 — C1의 그 버그다.
    """
    out = capture(
        ["--company", "테스트기업", "--archetype", "materials"],
        _result(archetype="materials"),
    )
    assert "(미보정)" not in out
    assert "materials" in out


def test_injected_thresholds_are_shown_separately(capture):
    result = score([], resolve_thresholds("materials", {"A1_poc_reproducibility": "3건"}))
    out = capture(["--company", "테스트기업", "--archetype", "materials"], result)
    assert "(미보정)" not in out
    assert "임계치 주입됨" in out


def test_calibration_note_is_shown(capture):
    out = capture(["--company", "테스트기업"], _result(archetype=None))
    assert "주의" in out


# --- 조사 결함 기록 (Important 6) ---


def test_research_notes_are_printed_in_text_mode(capture):
    note = "(B) 블록: 툴 호출 한도에 걸려 조사가 끝나기 전에 중단됐다"
    out = capture(["--company", "테스트기업"], _result(notes=[note]))
    assert note in out
    assert "조사 결함" in out


def test_research_notes_section_is_omitted_when_empty(capture):
    out = capture(["--company", "테스트기업"], _result(notes=[]))
    assert "조사 결함" not in out


def test_research_notes_precede_diligence_questions(capture):
    """커버리지 해석을 바꾸는 정보이므로 실사 질문 목록에 묻히면 안 된다."""
    note = "(A) 블록: 재시작 한도를 모두 썼다"
    out = capture(["--company", "테스트기업"], _result(notes=[note]))
    assert out.index(note) < out.index("실사에서 확인할 것")


# --- JSON 모드 ---


def test_json_mode_carries_notes_and_resolved_statuses(capture):
    note = "(C) 블록: 추출이 스키마 검증에 실패했다"
    out = capture(
        ["--company", "테스트기업", "--archetype", "materials", "--json"],
        _result(archetype="materials", notes=[note], evidence=[ev("A1_poc_reproducibility")]),
    )
    payload = json.loads(out)

    assert payload["research_notes"] == [note]
    assert payload["resolved_statuses"]["A1_poc_reproducibility"] == "MET"
    assert len(payload["resolved_statuses"]) == 10
    assert payload["calibration"]["archetype_injected"] is True
    assert payload["calibration"]["thresholds_injected"] is False


def test_json_mode_prints_only_json(capture):
    out = capture(["--company", "테스트기업", "--json"], _result())
    json.loads(out)  # 사람용 문구가 섞이면 여기서 깨진다


def test_missing_credentials_exit_code_and_no_traceback(capsys):
    def boom(*a, **k):
        raise RuntimeError("다음 환경변수가 없다: ANTHROPIC_API_KEY")

    with patch.object(cli, "evaluate", boom):
        with patch("sys.argv", ["proven-scalability", "--company", "테스트기업"]):
            assert cli.main() == 1

    captured = capsys.readouterr()
    assert "ANTHROPIC_API_KEY" in captured.err
    assert captured.out == ""


# --- --evidence 플래그 ---


def test_evidence_flag_is_forwarded_as_path(tmp_path):
    """--evidence 값이 evaluate에 Path로 그대로 전달돼야 한다."""
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text('{"items": []}', encoding="utf-8")

    seen_kwargs = {}

    def fake_evaluate(*args, **kwargs):
        seen_kwargs.update(kwargs)
        return _result()

    with patch.object(cli, "evaluate", fake_evaluate):
        with patch(
            "sys.argv",
            ["proven-scalability", "--company", "테스트기업", "--evidence", str(evidence_file)],
        ):
            assert cli.main() == 0

    assert seen_kwargs["evidence_path"] == evidence_file
    assert isinstance(seen_kwargs["evidence_path"], Path)


def test_evidence_flag_omitted_forwards_none(capture):
    """--evidence 없이 실행해도 정상 동작해야 한다 — DART 규칙 추출만으로 채점."""
    seen_kwargs = {}

    def fake_evaluate(*args, **kwargs):
        seen_kwargs.update(kwargs)
        return _result()

    with patch.object(cli, "evaluate", fake_evaluate):
        with patch("sys.argv", ["proven-scalability", "--company", "테스트기업"]):
            assert cli.main() == 0

    assert seen_kwargs["evidence_path"] is None


def test_evidence_file_error_exits_cleanly_without_traceback(capsys):
    """파일이 없거나 스키마 위반이면 EvidenceFileError가 traceback 없이 명확한 메시지로 나와야 한다."""

    def boom(*a, **k):
        raise EvidenceFileError("증거 파일이 없다: nope.json")

    with patch.object(cli, "evaluate", boom):
        with patch(
            "sys.argv",
            ["proven-scalability", "--company", "테스트기업", "--evidence", "nope.json"],
        ):
            assert cli.main() == 1

    captured = capsys.readouterr()
    assert "증거 파일이 없다" in captured.err
    assert captured.out == ""
    assert "Traceback" not in captured.err


def test_no_evidence_note_is_shown_when_present(capture):
    """증거 파일 없이 돌렸을 때의 안내 문구가 research_notes를 통해 그대로 드러나야 한다."""
    note = (
        "증거가 하나도 입력되지 않았다 — DART 추출 결과와 증거 파일이 모두 없다. "
        "전 항목 UNVERIFIABLE은 '조사했지만 없었다'가 아니라 '아무것도 조사되지 않았다'는 뜻이다."
    )
    out = capture(["--company", "테스트기업"], _result(notes=[note]))
    assert note in out


# --- 근거 등급 프로필 ---


def test_tier_composition_line_is_shown_when_met_criteria_exist(capture):
    result = _result(evidence=[ev("A1_poc_reproducibility", "MET", tier=3)])
    out = capture(["--company", "테스트기업"], result)
    assert "근거 구성" in out
    assert "MET 1건 중 0건은 1~2급, 1건은 3~4급" in out


def test_tier_composition_line_is_omitted_when_no_met_criteria(capture):
    out = capture(["--company", "테스트기업"], _result())
    assert "근거 구성" not in out


def test_evidence_file_warnings_appear_in_output(capture):
    """evidence_io가 스키마 위반 항목을 버리며 남긴 경고가 CLI 출력에 드러나야 한다."""
    note = "증거 파일 2번 항목을 스키마 위반으로 버렸다 (1건): criterion_id: 알 수 없는 값"
    out = capture(["--company", "테스트기업"], _result(notes=[note]))
    assert note in out
    assert "조사 결함" in out
