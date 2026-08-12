"""Proven Scalability 에이전트의 진입점.

LLM API를 호출하지 않는다. 증거는 두 경로로만 들어온다 — DART 규칙 추출(Task 2)과
사용자가 자신의 LLM 세션에서 만든 증거 파일(evidence_io, Task 3이 지시서를 만든다).
판정 자체는 여기서 하지 않는다 — scoring.score()가 순수 파이썬으로 한다.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.evidence_io import load_evidence
from agents.proven_scalability.schema import Evidence, ProvenScalabilityResult
from agents.proven_scalability.scoring import score

#: 저장소 루트의 .env를 명시적으로 가리킨다. load_dotenv()를 인자 없이 부르면
#: 현재 작업 디렉터리에서 위로 탐색하므로, 리포 루트가 아닌 곳에서 실행하면
#: 조용히 못 찾고 넘어간다 (DART 검증 중 실제로 겪은 문제).
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

#: LLM 층이 빠지면서 ANTHROPIC_API_KEY는 더 이상 필요 없다.
_REQUIRED_ENV_VARS = ("DART_API_KEY",)

_NO_EVIDENCE_NOTE = (
    "증거가 하나도 입력되지 않았다 — DART 추출 결과와 증거 파일이 모두 없다. "
    "전 항목 UNVERIFIABLE은 '조사했지만 없었다'가 아니라 '아무것도 조사되지 않았다'는 뜻이다."
)


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


def _extract_dart_evidence(company: str, dart_client) -> list[Evidence]:
    """DART 공시에서 결정적 규칙으로 Evidence를 뽑는다.

    TODO(Task 2): 감사보고서 주석의 수주잔고·무형자산·산업재산권 등을 규칙
    기반으로 파싱해 Evidence를 만든다. 이 자리는 아직 비어 있다 — 항상 빈
    리스트를 돌려준다.
    """
    return []


def evaluate(
    company: str,
    archetype: str | None = None,
    thresholds: dict[str, str] | None = None,
    evidence_path: Path | None = None,
    dart_client=None,
) -> ProvenScalabilityResult:
    """기업 하나를 기술성 축에서 판정한다.

    Args:
        company: 대상 기업명.
        archetype: PM 에이전트가 분류한 아키타입. None이면 중립 기준으로 실행하고
            결과에 uncalibrated로 명시한다. 본 에이전트가 자체 분류하지 않는다.
        thresholds: PM이 항목별로 내려준 임계치 오버라이드.
        evidence_path: 사용자의 LLM 세션이 만든 증거 JSON 경로. None이면 이 경로의
            증거는 없다.
        dart_client: DART 클라이언트. None이면 실제 조회 시점(Task 2)에 환경변수로
            생성한다. 테스트는 대역 객체를 넘겨 환경변수 점검을 건너뛴다.
    """
    if dart_client is None:
        _ensure_env_loaded()

    calibration = resolve_thresholds(archetype, thresholds)

    evidence: list[Evidence] = []
    notes: list[str] = []

    evidence.extend(_extract_dart_evidence(company, dart_client))

    if evidence_path is not None:
        file_evidence, warnings = load_evidence(evidence_path)
        evidence.extend(file_evidence)
        notes.extend(warnings)

    if not evidence:
        notes.append(_NO_EVIDENCE_NOTE)

    return score(evidence, calibration, research_notes=notes)
