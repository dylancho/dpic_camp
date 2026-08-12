"""Proven Scalability 에이전트의 진입점."""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.researcher import run_block
from agents.proven_scalability.schema import Block, Evidence, ProvenScalabilityResult
from agents.proven_scalability.scoring import score

_BLOCKS: tuple[Block, ...] = ("A", "B", "C")

#: 저장소 루트의 .env를 명시적으로 가리킨다. load_dotenv()를 인자 없이 부르면
#: 현재 작업 디렉터리에서 위로 탐색하므로, 리포 루트가 아닌 곳에서 실행하면
#: 조용히 못 찾고 넘어간다 (DART 검증 중 실제로 겪은 문제).
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

_REQUIRED_ENV_VARS = ("ANTHROPIC_API_KEY", "DART_API_KEY")


def _ensure_env_loaded() -> None:
    """필수 환경변수가 있는지 확인한다. 값은 절대 출력하지 않는다."""
    load_dotenv(_ENV_PATH)
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"다음 환경변수가 없다: {names}. "
            f"{_ENV_PATH} 에 값을 채우거나 셸 환경변수로 설정할 것."
        )


def evaluate(
    company: str,
    archetype: str | None = None,
    thresholds: dict[str, str] | None = None,
    client=None,
) -> ProvenScalabilityResult:
    """기업 하나를 기술성 축에서 판정한다.

    Args:
        company: 대상 기업명.
        archetype: PM 에이전트가 분류한 아키타입. None이면 중립 기준으로 실행하고
            결과에 uncalibrated로 명시한다. 본 에이전트가 자체 분류하지 않는다.
        thresholds: PM이 항목별로 내려준 임계치 오버라이드.
        client: anthropic 클라이언트. None이면 환경변수로 생성한다.
    """
    if client is None:
        _ensure_env_loaded()
        client = anthropic.Anthropic()
    calibration = resolve_thresholds(archetype, thresholds)

    evidence: list[Evidence] = []
    # 블록이 잘렸거나 추출이 실패한 사실을 결과까지 들고 간다. 이게 없으면 낮은
    # 커버리지가 '찾아봤지만 없었다'인지 '끝까지 못 봤다'인지 구분되지 않는다.
    notes: list[str] = []
    for block in _BLOCKS:
        evidence.extend(run_block(client, block, company, calibration, notes=notes))

    return score(evidence, calibration, research_notes=notes)
