"""레포의 파이썬이 LLM API를 호출하지 않음을 강제한다.

캠프 규칙상 제출 산출물은 모델을 호출할 수 없다. import 하나만 되살아나도
규칙 위반이므로 소스를 직접 훑는다.
"""

from pathlib import Path

import pytest

_PACKAGE = Path(__file__).resolve().parents[1] / "agents"
_FORBIDDEN = ("anthropic", "openai", "google.generativeai", "litellm", "ollama")


def _python_files() -> list[Path]:
    return sorted(_PACKAGE.rglob("*.py"))


def test_package_has_python_files():
    # 아래 테스트가 빈 목록을 훑고 통과하는 것을 막는다
    assert _python_files()


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.name)
def test_no_llm_sdk_import(path: Path):
    source = path.read_text(encoding="utf-8")
    for name in _FORBIDDEN:
        assert f"import {name}" not in source, f"{path.name} imports {name}"
        assert f"from {name}" not in source, f"{path.name} imports from {name}"


def test_anthropic_not_a_project_dependency():
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert "anthropic" not in pyproject
