"""Proven Scalability 에이전트의 진입점.

LLM API를 호출하지 않는다. 증거는 두 경로로만 들어온다 — DART 공시 규칙 추출
(extractors.dart_rules, B2·B3 두 항목만 다룬다)과 사용자가 자신의 LLM 세션에서 만든
증거 파일(evidence_io, docs/agent-instructions/의 md 지시서를 따른 결과). 판정 자체는
여기서 하지 않는다 — scoring.score()가 순수 파이썬으로 한다.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.evidence_io import load_evidence
from agents.proven_scalability.extractors import dart_rules
from agents.proven_scalability.schema import Evidence, ProvenScalabilityResult
from agents.proven_scalability.scoring import score
from agents.proven_scalability.tools.dart import DartClient, DartError

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


def _extract_dart_evidence(company: str, dart_client: DartClient) -> tuple[list[Evidence], list[str]]:
    """DART 공시에서 결정적 규칙(extractors.dart_rules)으로 Evidence를 뽑는다.

    dart_client가 실제 DartClient가 아니거나(테스트 대역) 예기치 못한 예외가 나면
    전체 판정을 죽이지 않고 경고로 남긴 채 빈 결과로 넘어간다 — DART는 증거의 두
    경로 중 하나일 뿐이고, 증거 파일 경로는 이것 없이도 온전히 동작해야 한다.
    dart_rules.extract 안에서 DartError는 이미 경고로 변환되므로, 여기서 잡는 것은
    그보다 더 예외적인 경우(잘못된 클라이언트 타입 등)다.
    """
    try:
        return dart_rules.extract(dart_client, company)
    except Exception as exc:  # noqa: BLE001 - 외부 클라이언트 실패가 전체를 죽이면 안 된다
        return [], [f"DART 규칙 추출 중 예외가 발생해 건너뛴다: {exc}"]


def _build_dart_client_from_env() -> tuple[DartClient | None, str | None]:
    """환경변수에서 DART 클라이언트를 만든다. 실패해도 예외를 던지지 않는다.

    Returns:
        (클라이언트 또는 None, 경고 메시지 또는 None). 키가 없으면 클라이언트 없이
        진행하되 그 사실을 research_notes에 남긴다 — 증거 파일만으로도 돌아가야 한다.
    """
    try:
        _ensure_env_loaded()
    except RuntimeError as exc:
        return None, f"DART 클라이언트를 만들 수 없다 — {exc} DART 없이 증거 파일만으로 진행한다."

    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return None, "DART_API_KEY가 없다 — DART 없이 증거 파일만으로 진행한다."

    try:
        return DartClient(api_key=api_key), None
    except DartError as exc:
        return None, f"DART 클라이언트 생성 실패 — {exc} DART 없이 증거 파일만으로 진행한다."


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
        dart_client: DART 클라이언트. None이면 환경변수(DART_API_KEY)에서 생성을
            시도하고, 키가 없거나 생성에 실패해도 예외를 던지지 않고 경고만 남긴 채
            DART 없이 진행한다 — 증거 파일 경로가 이것 없이도 온전히 동작해야 한다.
            테스트는 대역 객체를 넘겨 환경변수 점검을 건너뛴다.
    """
    calibration = resolve_thresholds(archetype, thresholds)

    evidence: list[Evidence] = []
    notes: list[str] = []

    client = dart_client
    owns_client = False
    if client is None:
        client, warning = _build_dart_client_from_env()
        owns_client = client is not None
        if warning is not None:
            notes.append(warning)

    if client is not None:
        dart_evidence, dart_warnings = _extract_dart_evidence(company, client)
        evidence.extend(dart_evidence)
        notes.extend(dart_warnings)
        if owns_client:
            client.close()

    if evidence_path is not None:
        file_evidence, warnings = load_evidence(evidence_path)
        evidence.extend(file_evidence)
        notes.extend(warnings)

    if not evidence:
        notes.append(_NO_EVIDENCE_NOTE)

    return score(evidence, calibration, research_notes=notes)
