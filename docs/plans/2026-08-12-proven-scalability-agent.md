# Proven Scalability 에이전트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** pre-IPO 기업의 하우스 투자 원칙 (d) Proven Scalability(기술성 25점)를 판정하는 하위 에이전트를 만든다.

**Architecture:** LLM은 증거만 수집하고, 배점·게이트·verdict은 순수 Python이 결정론적으로 계산한다. 리서처는 2단계로 동작한다 — Tool Runner로 자유롭게 조사한 뒤, `client.messages.parse`로 그 전문을 `Evidence[]` 스키마에 강제 캐스팅한다. 아키타입 임계치는 PM 에이전트에서 주입받으며 자체 추정하지 않는다.

**Tech Stack:** Python 3.11+ · `anthropic` SDK (Tool Runner + 구조화 출력) · `pydantic` v2 · `httpx` · `pytest`

## Global Constraints

- 모델 ID는 `claude-opus-5` 고정. 다른 문자열을 쓰지 않는다
- `thinking` 파라미터를 명시하지 않는다 — Claude Opus 5는 기본이 adaptive다
- `temperature` / `top_p` / `top_k` / `budget_tokens`를 쓰지 않는다 — Claude Opus 5에서 400이다
- 비스트리밍 요청의 `max_tokens`는 16000
- 모든 API 응답에서 `response.content`를 읽기 **전에** `stop_reason == "refusal"`을 먼저 확인한다
- `scoring.py`·`criteria.py`·`schema.py`에는 `anthropic` import가 없다. LLM 호출 금지
- 배점: A 충족 1/2/3개 → 8/10/12, B 충족 2/3/4개 → 5/7/8, C 충족 1/2/3개 → 2/4/5
- 게이트: A는 `MET ≥ 1`, B는 `MET ≥ 2`. 미충족 시 해당 블록 0점 + `gate_failed` 플래그
- 출처 등급 1~4. 3~4급 근거만으로 뒷받침된 항목은 `MET` → `UNVERIFIABLE`로 강등
- 비밀값(DART API 키)은 `.env`에서만 읽고 커밋하지 않는다. 로그·예외 메시지에 출력하지 않는다
- 브랜치는 `Proven-Scalability-agent`. `agents/proven_scalability/`와 `tests/` 밖은 건드리지 않는다

---

## File Structure

| 파일 | 책임 |
|---|---|
| `pyproject.toml` | 의존성·pytest 설정 |
| `.env.example` | 필요한 환경변수 이름만 (값 없음) |
| `agents/proven_scalability/schema.py` | `Evidence`, `Status`, `SourceTier`, `Calibration`, `BlockScores`, `ProvenScalabilityResult` |
| `agents/proven_scalability/criteria.py` | A/B/C 항목 정의 + 아키타입별 임계치 치환 |
| `agents/proven_scalability/scoring.py` | 순수 함수. `Evidence[]` → 점수·게이트·verdict·커버리지·실사질문 |
| `agents/proven_scalability/tools/dart.py` | DART OpenAPI 클라이언트 + `@beta_tool` |
| `agents/proven_scalability/tools/web.py` | 웹 검색 서버툴 정의 |
| `agents/proven_scalability/tools/kipris.py` | 인터페이스만. 키 미확보 (§ Task 5) |
| `agents/proven_scalability/prompts.py` | 블록별 조사 프롬프트 + 추출 프롬프트 |
| `agents/proven_scalability/researcher.py` | 2단계 리서처 (조사 → 추출) |
| `agents/proven_scalability/agent.py` | 오케스트레이션. 3개 리서처 실행 → scoring → 결과 |
| `tests/test_schema.py` … `tests/test_agent.py` | 대응 테스트 |
| `tests/fixtures/evidence.py` | 재사용 가능한 Evidence 픽스처 빌더 |

Task 1~4는 LLM 없이 완결되고 전부 결정론적으로 테스트된다. Task 5~8만 네트워크를 탄다.

---

### Task 1: 프로젝트 스캐폴딩 + 스키마

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `agents/__init__.py`, `agents/proven_scalability/__init__.py`
- Create: `agents/proven_scalability/schema.py`
- Test: `tests/__init__.py`, `tests/test_schema.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `Status` — `Literal["MET", "NOT_MET", "UNVERIFIABLE"]`
  - `Evidence(criterion_id: str, status: Status, source_tier: int, source_url: str | None, quote: str, extracted_value: str | None)`
  - `Calibration(archetype: str, thresholds: dict[str, str], injected: bool, note: str | None)`
  - `BlockScores(a: int, b: int, c: int)` — `.total` 프로퍼티
  - `ProvenScalabilityResult(verdict, score, block_scores, gate_failed, evidence_coverage, calibration, evidence, diligence_questions)`

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[project]
name = "proven-scalability-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.116.0",
    "pydantic>=2.7",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["live: 실제 네트워크를 타는 테스트 (기본 실행에서 제외)"]
addopts = "-m 'not live'"
```

- [ ] **Step 2: `.env.example` 와 `.gitignore` 작성**

`.env.example` — 값은 절대 채우지 않는다:

```
# DART OpenAPI 인증키 — https://opendart.fss.or.kr 에서 발급
DART_API_KEY=
# Anthropic API 키
ANTHROPIC_API_KEY=
```

`.gitignore`:

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_schema.py`:

```python
import pytest
from pydantic import ValidationError

from agents.proven_scalability.schema import (
    BlockScores,
    Calibration,
    Evidence,
    ProvenScalabilityResult,
)


def test_evidence_requires_valid_tier():
    with pytest.raises(ValidationError):
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MET",
            source_tier=5,  # 1~4만 허용
            source_url="https://example.com",
            quote="...",
        )


def test_evidence_rejects_unknown_status():
    with pytest.raises(ValidationError):
        Evidence(
            criterion_id="A1_poc_reproducibility",
            status="MAYBE",
            source_tier=1,
            source_url=None,
            quote="...",
        )


def test_block_scores_total():
    assert BlockScores(a=12, b=8, c=5).total == 25
    assert BlockScores(a=0, b=0, c=0).total == 0


def test_result_round_trips_through_json():
    result = ProvenScalabilityResult(
        verdict="PASS",
        score=25,
        block_scores=BlockScores(a=12, b=8, c=5),
        gate_failed=[],
        evidence_coverage=1.0,
        calibration=Calibration(
            archetype="materials", thresholds={"A3": "pilot run >= 2"}, injected=True
        ),
        evidence=[],
        diligence_questions=[],
    )
    restored = ProvenScalabilityResult.model_validate_json(result.model_dump_json())
    assert restored == result
```

- [ ] **Step 4: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.schema'`

- [ ] **Step 5: `schema.py` 구현**

```python
"""Proven Scalability 에이전트의 데이터 계약.

이 모듈에는 LLM 호출이 없다. 순수 데이터 정의만 둔다.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Status = Literal["MET", "NOT_MET", "UNVERIFIABLE"]
Verdict = Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"]
Block = Literal["A", "B", "C"]

#: 1 = DART 공시·감사보고서 주석·등록특허 원문·거래소 기술성 평가
#: 2 = 제3자 공인 시험성적서·독립 인증기관·peer-reviewed 논문
#: 3 = 언론 보도·산업 리포트
#: 4 = 회사 자체 발표·IR 자료·홈페이지
SourceTier = Annotated[int, Field(ge=1, le=4)]


class Evidence(BaseModel):
    """한 항목에 대한 하나의 근거. 리서처가 반환하는 유일한 타입."""

    criterion_id: str
    status: Status
    source_tier: SourceTier
    source_url: str | None = None
    quote: str = Field(description="판단 근거가 된 원문 인용")
    extracted_value: str | None = Field(
        default=None,
        description="PoC 건수·가동시간·특허 건수·석사 비중 등 정량값. 원문 표기 그대로",
    )


class Calibration(BaseModel):
    """PM 에이전트가 내려준 아키타입과 임계치. 본 에이전트는 분류하지 않는다."""

    archetype: str
    thresholds: dict[str, str] = Field(default_factory=dict)
    injected: bool = Field(
        description="False면 PM 주입 없이 아키타입 중립 기준으로 실행됐다는 뜻"
    )
    note: str | None = None


class BlockScores(BaseModel):
    a: int = Field(ge=0, le=12)
    b: int = Field(ge=0, le=8)
    c: int = Field(ge=0, le=5)

    @property
    def total(self) -> int:
        return self.a + self.b + self.c


class ProvenScalabilityResult(BaseModel):
    verdict: Verdict
    score: int = Field(ge=0, le=25)
    block_scores: BlockScores
    gate_failed: list[Block]
    evidence_coverage: float = Field(
        ge=0.0, le=1.0, description="조사 항목 중 UNVERIFIABLE이 아닌 비율"
    )
    calibration: Calibration
    evidence: list[Evidence]
    diligence_questions: list[str]
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `python -m pytest tests/test_schema.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: 커밋**

```bash
git add pyproject.toml .env.example .gitignore agents tests
git commit -m "feat(schema): Evidence·Calibration·ProvenScalabilityResult 데이터 계약 추가"
```

---

### Task 2: 판정 기준과 아키타입 임계치

**Files:**
- Create: `agents/proven_scalability/criteria.py`
- Test: `tests/test_criteria.py`

**Interfaces:**
- Consumes: `schema.Block`
- Produces:
  - `Criterion(id: str, block: Block, label: str, default_threshold: str)` (dataclass)
  - `CRITERIA: tuple[Criterion, ...]` — A 3개 + B 4개 + C 3개 = 10개
  - `criteria_for(block: Block) -> tuple[Criterion, ...]`
  - `criterion_ids() -> frozenset[str]`
  - `resolve_thresholds(archetype: str | None, injected: dict[str, str] | None) -> Calibration`
  - `ARCHETYPE_OVERRIDES: dict[str, dict[str, str]]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_criteria.py`:

```python
from agents.proven_scalability.criteria import (
    CRITERIA,
    criteria_for,
    criterion_ids,
    resolve_thresholds,
)


def test_block_composition():
    assert len(criteria_for("A")) == 3
    assert len(criteria_for("B")) == 4
    assert len(criteria_for("C")) == 3
    assert len(CRITERIA) == 10


def test_criterion_ids_are_unique():
    assert len(criterion_ids()) == len(CRITERIA)


def test_software_archetype_replaces_hardware_thresholds():
    cal = resolve_thresholds("software_ai_robotics", None)
    assert cal.archetype == "software_ai_robotics"
    # 하드웨어의 1,000시간 기준을 그대로 적용하지 않는다
    assert "1,000" not in cal.thresholds["A3_field_operation_hours"]
    # C 블록도 SW 문구로 치환된다
    assert cal.thresholds["C1_capacity_plan"] != _default("C1_capacity_plan")


def test_deep_tech_archetype_does_not_use_hardware_hours():
    cal = resolve_thresholds("deep_tech", None)
    assert "1,000" not in cal.thresholds["A3_field_operation_hours"]


def test_injected_thresholds_win_over_archetype_defaults():
    cal = resolve_thresholds(
        "materials", {"A1_poc_reproducibility": "고객 qualification 3건 이상"}
    )
    assert cal.thresholds["A1_poc_reproducibility"] == "고객 qualification 3건 이상"
    assert cal.injected is True


def test_missing_calibration_is_flagged_not_guessed():
    cal = resolve_thresholds(None, None)
    assert cal.injected is False
    assert cal.archetype == "uncalibrated"
    assert cal.note is not None
    # 중립 기준은 원칙 원문 그대로
    assert cal.thresholds["A3_field_operation_hours"] == _default(
        "A3_field_operation_hours"
    )


def _default(criterion_id: str) -> str:
    return next(c.default_threshold for c in CRITERIA if c.id == criterion_id)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_criteria.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.criteria'`

- [ ] **Step 3: `criteria.py` 구현**

```python
"""하우스 투자 원칙 (d)의 판정 항목과 아키타입별 임계치.

하우스 기준이 바뀌면 이 파일만 고친다. scoring.py는 건드릴 필요가 없다.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.proven_scalability.schema import Block, Calibration


@dataclass(frozen=True)
class Criterion:
    id: str
    block: Block
    label: str
    default_threshold: str


CRITERIA: tuple[Criterion, ...] = (
    # (A) 기술 작동 증명 — 게이트 1개 이상
    Criterion(
        "A1_poc_reproducibility",
        "A",
        "PoC 재현성",
        "서로 다른 고객·환경에서 PoC 2회 이상, 핵심 성능 KPI가 ±10~20% 내 재현",
    ),
    Criterion(
        "A2_third_party_validation",
        "A",
        "제3자 검증",
        "제3자 시험성적서 또는 독립 인증 2건 이상 (Founder 자체 테스트만 있으면 불인정)",
    ),
    Criterion(
        "A3_field_operation_hours",
        "A",
        "실환경 가동",
        "실환경 누적 가동 1,000시간 이상",
    ),
    # (B) 해자 — 게이트 2개 이상
    Criterion(
        "B1_exchange_tech_grade",
        "B",
        "거래소 기술성 평가",
        "거래소 기술성 평가 A 이상 (기술특례상장 기준 등급)",
    ),
    Criterion(
        "B2_registered_patents",
        "B",
        "등록 특허",
        "등록 특허 3건 이상 (출원 아님). 핵심 청구항의 경쟁사 회피 난이도를 함께 본다",
    ),
    Criterion(
        "B3_domain_expertise",
        "B",
        "도메인 전문성",
        "관련 도메인 석사 이상 인력 비중 60% 이상",
    ),
    Criterion(
        "B4_lab_publication_track",
        "B",
        "랩·논문 이력",
        "핵심 인력이 관련 도메인 랩실 근무 이력, peer-reviewed 논문, 또는 핵심 특허를 보유",
    ),
    # (C) Scale-up 준비 — 게이트 없음
    Criterion(
        "C1_capacity_plan",
        "C",
        "생산능력 확대 계획",
        "라인·플랜트 증설 로드맵이 시점과 규모로 제시된다",
    ),
    Criterion(
        "C2_capex_funding",
        "C",
        "capex 조달 계획",
        "증설에 필요한 자금의 출처가 특정된다 (조달 완료 또는 확정 계획)",
    ),
    Criterion(
        "C3_supply_chain",
        "C",
        "공급망 확보",
        "핵심 원료·부품의 공급 계약 또는 이중 소싱이 확보되어 있다",
    ),
)

#: 아키타입별로 원칙의 문구를 치환한다. 여기 없는 항목은 default_threshold를 쓴다.
ARCHETYPE_OVERRIDES: dict[str, dict[str, str]] = {
    "deep_tech": {
        "A3_field_operation_hours": (
            "Pilot plant 가동 + TRL 6 이상. 하드웨어의 1,000시간 기준을 적용하지 않는다"
        ),
        "A2_third_party_validation": "제3자 검증 2건 이상 (장기 validation 허용)",
    },
    "materials": {
        "A1_poc_reproducibility": "Pilot run 2회 이상 + 고객 qualification 1건 이상, 재현성 ±10~20%",
        "A3_field_operation_hours": "Pilot run 누적 검증. 시간 기준 대신 배치 수와 수율 재현성으로 본다",
    },
    "industrial_hardware": {},  # 원칙 원문이 곧 하드웨어 기준이다
    "energy_infra": {
        "A3_field_operation_hours": "실증 사이트 가동 + 성능보증(PPA 또는 성능계약) 체결",
    },
    "recycling": {
        "A1_poc_reproducibility": "파일럿 recovery rate 검증 2회 이상",
        "A3_field_operation_hours": "파일럿 플랜트 누적 처리량과 recovery rate 재현성",
    },
    "software_ai_robotics": {
        "A1_poc_reproducibility": "서로 다른 환경에 배포 2건 이상, 핵심 성능 재현",
        "A3_field_operation_hours": "프로덕션 배포 후 운영 기간과 uptime. 가동시간 기준을 적용하지 않는다",
        "C1_capacity_plan": "인프라 확장 계획 (트래픽 증가에 대한 아키텍처·비용 대응)",
        "C2_capex_funding": "조직·인력 확장 계획 (채용 규모와 자금 출처)",
        "C3_supply_chain": "재현 가능한 배포 파이프라인 (CI/CD, 롤백, 모니터링)",
    },
}

_UNCALIBRATED_NOTE = (
    "PM 에이전트의 아키타입 임계치가 주입되지 않아 원칙 원문의 중립 기준으로 실행했다. "
    "산업 특성이 반영되지 않았으므로 점수를 그대로 신뢰하지 말 것."
)


def criteria_for(block: Block) -> tuple[Criterion, ...]:
    return tuple(c for c in CRITERIA if c.block == block)


def criterion_ids() -> frozenset[str]:
    return frozenset(c.id for c in CRITERIA)


def resolve_thresholds(
    archetype: str | None, injected: dict[str, str] | None
) -> Calibration:
    """적용할 임계치를 확정한다.

    우선순위는 PM 주입값 > 아키타입 오버라이드 > 원칙 원문이다.
    아키타입이 없으면 자체 추정하지 않고 중립 기준으로 실행하되 그 사실을 명시한다.
    """
    thresholds = {c.id: c.default_threshold for c in CRITERIA}

    if archetype is None:
        return Calibration(
            archetype="uncalibrated",
            thresholds=thresholds,
            injected=False,
            note=_UNCALIBRATED_NOTE,
        )

    thresholds.update(ARCHETYPE_OVERRIDES.get(archetype, {}))
    note = None
    if archetype not in ARCHETYPE_OVERRIDES:
        note = f"알 수 없는 아키타입 '{archetype}' — 원칙 원문의 중립 기준을 적용했다."
    if injected:
        thresholds.update(injected)

    return Calibration(
        archetype=archetype,
        thresholds=thresholds,
        injected=bool(injected),
        note=note,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_criteria.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 커밋**

```bash
git add agents/proven_scalability/criteria.py tests/test_criteria.py
git commit -m "feat(criteria): A/B/C 판정 항목 10개와 아키타입별 임계치 치환 추가"
```

---

### Task 3: 등급 필터와 배점 (결정론 계층)

이 태스크가 설계의 심장이다. LLM 없이 전부 테스트된다.

**Files:**
- Create: `agents/proven_scalability/scoring.py`
- Create: `tests/fixtures/__init__.py`, `tests/fixtures/evidence.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `schema.Evidence`, `schema.Status`, `schema.BlockScores`, `criteria.criteria_for`, `criteria.criterion_ids`
- Produces:
  - `apply_tier_filter(evidence: list[Evidence]) -> list[Evidence]`
  - `resolve_statuses(evidence: list[Evidence]) -> dict[str, Status]` — 항목별 최종 상태 (10개 전부, 증거 없으면 `UNVERIFIABLE`)
  - `score_block(block: Block, statuses: dict[str, Status]) -> int`
  - `gate_failures(statuses: dict[str, Status]) -> list[Block]`
  - `decide_verdict(statuses: dict[str, Status]) -> Verdict`
  - `evidence_coverage(statuses: dict[str, Status]) -> float`
  - `build_diligence_questions(statuses: dict[str, Status], calibration: Calibration) -> list[str]`
  - `score(evidence, calibration) -> ProvenScalabilityResult`

**핵심 규칙 세 가지**
1. **등급 필터** — 어떤 항목이 3~4급 근거만으로 `MET`이면 `UNVERIFIABLE`로 강등. 1~2급 `MET`이 하나라도 있으면 유지
2. **상태 합성** — 한 항목에 여러 증거가 있으면 `MET` > `NOT_MET` > `UNVERIFIABLE` 순으로 강한 것이 이긴다 (필터 적용 후)
3. **verdict** — 게이트 통과 시 `PASS`. 실패했고 그 블록에 `UNVERIFIABLE`이 하나라도 있으면 `INSUFFICIENT_EVIDENCE`. 전부 `NOT_MET`이면 `FAIL`

- [ ] **Step 1: 픽스처 빌더 작성**

`tests/fixtures/evidence.py`:

```python
from agents.proven_scalability.schema import Evidence, Status


def ev(
    criterion_id: str,
    status: Status = "MET",
    tier: int = 1,
    value: str | None = None,
) -> Evidence:
    """테스트용 Evidence 빌더. 기본은 1급 근거의 MET."""
    return Evidence(
        criterion_id=criterion_id,
        status=status,
        source_tier=tier,
        source_url="https://example.com/doc",
        quote=f"{criterion_id} 관련 인용",
        extracted_value=value,
    )
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_scoring.py`:

```python
from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.schema import BlockScores
from agents.proven_scalability.scoring import (
    decide_verdict,
    evidence_coverage,
    gate_failures,
    resolve_statuses,
    score,
    score_block,
)
from tests.fixtures.evidence import ev

CAL = resolve_thresholds("industrial_hardware", None)


# --- 등급 필터 ---


def test_tier_3_only_met_is_demoted_to_unverifiable():
    statuses = resolve_statuses([ev("A1_poc_reproducibility", "MET", tier=3)])
    assert statuses["A1_poc_reproducibility"] == "UNVERIFIABLE"


def test_tier_4_only_met_is_demoted():
    statuses = resolve_statuses([ev("A2_third_party_validation", "MET", tier=4)])
    assert statuses["A2_third_party_validation"] == "UNVERIFIABLE"


def test_tier_1_met_survives_alongside_tier_3():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility", "MET", tier=3),
            ev("A1_poc_reproducibility", "MET", tier=1),
        ]
    )
    assert statuses["A1_poc_reproducibility"] == "MET"


def test_tier_3_not_met_is_not_demoted():
    # 강등은 MET에만 적용된다. 미달 판정은 등급과 무관하게 유지
    statuses = resolve_statuses([ev("A3_field_operation_hours", "NOT_MET", tier=3)])
    assert statuses["A3_field_operation_hours"] == "NOT_MET"


# --- 상태 합성 ---


def test_met_beats_not_met_for_same_criterion():
    statuses = resolve_statuses(
        [
            ev("B2_registered_patents", "NOT_MET", tier=1),
            ev("B2_registered_patents", "MET", tier=1),
        ]
    )
    assert statuses["B2_registered_patents"] == "MET"


def test_unscanned_criterion_defaults_to_unverifiable():
    statuses = resolve_statuses([])
    assert len(statuses) == 10
    assert set(statuses.values()) == {"UNVERIFIABLE"}


# --- 배점 ---


def test_block_a_scores_by_count():
    ids = [
        "A1_poc_reproducibility",
        "A2_third_party_validation",
        "A3_field_operation_hours",
    ]
    for n, expected in [(1, 8), (2, 10), (3, 12)]:
        statuses = resolve_statuses([ev(i) for i in ids[:n]])
        assert score_block("A", statuses) == expected


def test_block_a_zero_when_gate_fails():
    assert score_block("A", resolve_statuses([])) == 0


def test_block_b_scores_by_count():
    ids = [
        "B1_exchange_tech_grade",
        "B2_registered_patents",
        "B3_domain_expertise",
        "B4_lab_publication_track",
    ]
    for n, expected in [(2, 5), (3, 7), (4, 8)]:
        statuses = resolve_statuses([ev(i) for i in ids[:n]])
        assert score_block("B", statuses) == expected


def test_block_b_zero_with_only_one_met():
    statuses = resolve_statuses([ev("B1_exchange_tech_grade")])
    assert score_block("B", statuses) == 0


def test_block_c_scores_by_count_without_gate():
    ids = ["C1_capacity_plan", "C2_capex_funding", "C3_supply_chain"]
    for n, expected in [(0, 0), (1, 2), (2, 4), (3, 5)]:
        statuses = resolve_statuses([ev(i) for i in ids[:n]])
        assert score_block("C", statuses) == expected


# --- 게이트와 verdict ---


def test_gate_failures_lists_both_blocks():
    assert gate_failures(resolve_statuses([])) == ["A", "B"]


def test_no_gate_failure_when_thresholds_met():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
        ]
    )
    assert gate_failures(statuses) == []


def test_verdict_pass_when_both_gates_clear():
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
        ]
    )
    assert decide_verdict(statuses) == "PASS"


def test_verdict_fail_when_every_criterion_investigated_and_short():
    # 모든 항목을 조사했고 전부 기준 미달 — 조사가 끝났다는 뜻
    all_ids = list(resolve_statuses([]).keys())
    statuses = resolve_statuses([ev(i, "NOT_MET") for i in all_ids])
    assert decide_verdict(statuses) == "FAIL"


def test_verdict_insufficient_when_unverifiable_remains_in_failed_gate():
    all_ids = list(resolve_statuses([]).keys())
    evidence = [ev(i, "NOT_MET") for i in all_ids if i != "A2_third_party_validation"]
    statuses = resolve_statuses(evidence)  # A2만 UNVERIFIABLE로 남는다
    assert statuses["A2_third_party_validation"] == "UNVERIFIABLE"
    assert decide_verdict(statuses) == "INSUFFICIENT_EVIDENCE"


def test_unverifiable_in_passing_gate_does_not_block_pass():
    # A게이트는 통과. B의 UNVERIFIABLE은 verdict를 바꾸지 않는다
    statuses = resolve_statuses(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
        ]
    )
    assert decide_verdict(statuses) == "PASS"


# --- 커버리지 ---


def test_coverage_counts_non_unverifiable_ratio():
    statuses = resolve_statuses(
        [ev("A1_poc_reproducibility"), ev("B1_exchange_tech_grade", "NOT_MET")]
    )
    assert evidence_coverage(statuses) == 0.2  # 10개 중 2개


def test_coverage_is_zero_with_no_evidence():
    assert evidence_coverage(resolve_statuses([])) == 0.0


# --- 결정론 ---


def test_same_evidence_always_yields_same_result():
    evidence = [
        ev("A1_poc_reproducibility"),
        ev("A2_third_party_validation", "NOT_MET"),
        ev("B1_exchange_tech_grade"),
        ev("B2_registered_patents", tier=2),
        ev("C1_capacity_plan"),
    ]
    first = score(evidence, CAL)
    second = score(list(reversed(evidence)), CAL)
    assert first.score == second.score
    assert first.verdict == second.verdict
    assert first.block_scores == second.block_scores


def test_score_assembles_full_result():
    result = score(
        [
            ev("A1_poc_reproducibility"),
            ev("B1_exchange_tech_grade"),
            ev("B2_registered_patents"),
            ev("C1_capacity_plan"),
        ],
        CAL,
    )
    assert result.verdict == "PASS"
    assert result.block_scores == BlockScores(a=8, b=5, c=2)
    assert result.score == 15
    assert result.gate_failed == []
    assert result.diligence_questions  # UNVERIFIABLE 항목이 남아 있으므로 비어 있지 않다
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.scoring'`

- [ ] **Step 4: `scoring.py` 구현**

```python
"""등급 필터·게이트·배점·verdict.

이 모듈에는 LLM 호출이 없다. 같은 Evidence 집합이면 항상 같은 결과가 나온다.
"""

from __future__ import annotations

from agents.proven_scalability.criteria import CRITERIA, criteria_for
from agents.proven_scalability.schema import (
    Block,
    BlockScores,
    Calibration,
    Evidence,
    ProvenScalabilityResult,
    Status,
    Verdict,
)

#: 3급(언론)·4급(회사 자체 발표) 근거만으로는 MET을 인정하지 않는다.
#: 원칙의 "Founder 자체 테스트만 있으면 불인정"을 코드로 강제하는 장치다.
_CREDIBLE_TIERS = frozenset({1, 2})

#: 충족 개수 → 점수. 게이트 미달 구간은 아예 키에 없다.
_SCORE_TABLE: dict[Block, dict[int, int]] = {
    "A": {1: 8, 2: 10, 3: 12},
    "B": {2: 5, 3: 7, 4: 8},
    "C": {1: 2, 2: 4, 3: 5},
}

#: 게이트 최소 충족 개수. C는 게이트가 없다.
_GATE_MINIMUM: dict[Block, int] = {"A": 1, "B": 2}

_STATUS_STRENGTH: dict[Status, int] = {"UNVERIFIABLE": 0, "NOT_MET": 1, "MET": 2}


def apply_tier_filter(evidence: list[Evidence]) -> list[Evidence]:
    """신뢰할 수 없는 출처만으로 뒷받침된 MET을 UNVERIFIABLE로 강등한다.

    강등은 MET에만 적용한다. NOT_MET은 등급과 무관하게 유지한다 —
    "언론 보도로 미달이 확인됐다"는 판정을 뒤집을 이유가 없기 때문이다.
    """
    credible: set[str] = {
        e.criterion_id
        for e in evidence
        if e.status == "MET" and e.source_tier in _CREDIBLE_TIERS
    }
    filtered: list[Evidence] = []
    for e in evidence:
        if e.status == "MET" and e.criterion_id not in credible:
            filtered.append(e.model_copy(update={"status": "UNVERIFIABLE"}))
        else:
            filtered.append(e)
    return filtered


def resolve_statuses(evidence: list[Evidence]) -> dict[str, Status]:
    """항목별 최종 상태를 확정한다. 조사되지 않은 항목은 UNVERIFIABLE이다."""
    statuses: dict[str, Status] = {c.id: "UNVERIFIABLE" for c in CRITERIA}
    for e in apply_tier_filter(evidence):
        if e.criterion_id not in statuses:
            continue  # 알 수 없는 항목 ID는 조용히 버린다
        if _STATUS_STRENGTH[e.status] > _STATUS_STRENGTH[statuses[e.criterion_id]]:
            statuses[e.criterion_id] = e.status
    return statuses


def _met_count(block: Block, statuses: dict[str, Status]) -> int:
    return sum(1 for c in criteria_for(block) if statuses[c.id] == "MET")


def score_block(block: Block, statuses: dict[str, Status]) -> int:
    """게이트를 넘지 못한 블록은 0점이다."""
    return _SCORE_TABLE[block].get(_met_count(block, statuses), 0)


def gate_failures(statuses: dict[str, Status]) -> list[Block]:
    return [
        block
        for block, minimum in _GATE_MINIMUM.items()
        if _met_count(block, statuses) < minimum
    ]


def decide_verdict(statuses: dict[str, Status]) -> Verdict:
    """게이트 미충족의 '원인'으로 갈린다. 커버리지 수치는 verdict를 바꾸지 않는다."""
    failed = gate_failures(statuses)
    if not failed:
        return "PASS"
    recoverable = any(
        statuses[c.id] == "UNVERIFIABLE" for b in failed for c in criteria_for(b)
    )
    return "INSUFFICIENT_EVIDENCE" if recoverable else "FAIL"


def evidence_coverage(statuses: dict[str, Status]) -> float:
    resolved = sum(1 for s in statuses.values() if s != "UNVERIFIABLE")
    return resolved / len(statuses)


def build_diligence_questions(
    statuses: dict[str, Status], calibration: Calibration
) -> list[str]:
    """UNVERIFIABLE 항목을 실사 질문으로 바꾼다. CRITERIA 정의 순서를 따른다.

    판정 기준은 반드시 calibration의 임계치를 쓴다. 원칙 원문(default_threshold)을
    그대로 쓰면 SW 기업 실사 질문에 "가동 1,000시간" 같은, 아키타입이 적용하지
    말라고 명시한 기준이 찍힌다.
    """
    return [
        f"[{c.id}] {c.label} — 공개 자료에서 확인할 수 없었다. "
        f"판정 기준: {calibration.thresholds.get(c.id, c.default_threshold)}"
        for c in CRITERIA
        if statuses[c.id] == "UNVERIFIABLE"
    ]


def score(
    evidence: list[Evidence], calibration: Calibration
) -> ProvenScalabilityResult:
    statuses = resolve_statuses(evidence)
    blocks = BlockScores(
        a=score_block("A", statuses),
        b=score_block("B", statuses),
        c=score_block("C", statuses),
    )
    return ProvenScalabilityResult(
        verdict=decide_verdict(statuses),
        score=blocks.total,
        block_scores=blocks,
        gate_failed=gate_failures(statuses),
        evidence_coverage=evidence_coverage(statuses),
        calibration=calibration,
        evidence=evidence,
        diligence_questions=build_diligence_questions(statuses, calibration),
    )
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: PASS (21 passed)

- [ ] **Step 6: 전체 테스트 재확인**

Run: `python -m pytest -v`
Expected: PASS (31 passed)

- [ ] **Step 7: 커밋**

```bash
git add agents/proven_scalability/scoring.py tests/test_scoring.py tests/fixtures
git commit -m "feat(scoring): 등급 필터·게이트·배점·verdict 결정론 계층 추가"
```

---

### Task 4: DART 툴

**Files:**
- Create: `agents/proven_scalability/tools/__init__.py`
- Create: `agents/proven_scalability/tools/dart.py`
- Test: `tests/test_dart.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `DartClient(api_key: str, http: httpx.Client | None = None)`
  - `.find_corp_code(company_name: str) -> str | None`
  - `.list_disclosures(corp_code: str, begin: str, end: str, kind: str | None = None) -> list[dict]`
  - `.fetch_document(rcept_no: str) -> str`
  - `dart_search(company_name: str, keyword: str) -> str` — `@beta_tool` 데코레이트된 툴 함수
  - `DartError(Exception)`

**Note:** DART는 `corpCode.xml`을 zip으로 내려주는데 20MB 남짓이다. 매 호출마다 받지 않고 `~/.cache/dpic/corp_codes.json`에 캐시한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_dart.py`:

```python
import httpx
import pytest

from agents.proven_scalability.tools.dart import DartClient, DartError


def _client(handler) -> DartClient:
    transport = httpx.MockTransport(handler)
    return DartClient(api_key="test-key", http=httpx.Client(transport=transport))


def test_list_disclosures_returns_rows():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "opendart.fss.or.kr" in str(request.url)
        return httpx.Response(
            200,
            json={
                "status": "000",
                "message": "정상",
                "list": [
                    {
                        "corp_name": "테스트",
                        "report_nm": "사업보고서",
                        "rcept_no": "20250315000001",
                        "rcept_dt": "20250315",
                    }
                ],
            },
        )

    rows = _client(handler).list_disclosures("00126380", "20240101", "20251231")
    assert len(rows) == 1
    assert rows[0]["rcept_no"] == "20250315000001"


def test_no_results_status_returns_empty_list_not_error():
    # DART는 조회 결과가 없을 때 status 013을 준다. 이건 에러가 아니다
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "013", "message": "조회된 데이터가 없습니다."})

    assert _client(handler).list_disclosures("00126380", "20240101", "20251231") == []


def test_api_error_status_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "020", "message": "요청 제한 초과"})

    with pytest.raises(DartError, match="020"):
        _client(handler).list_disclosures("00126380", "20240101", "20251231")


def test_api_key_never_appears_in_error_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "010", "message": "등록되지 않은 키"})

    with pytest.raises(DartError) as exc:
        _client(handler).list_disclosures("00126380", "20240101", "20251231")
    assert "test-key" not in str(exc.value)


@pytest.mark.live
def test_live_dart_connection():
    """실제 DART 호출. `pytest -m live`로만 실행된다."""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DART_API_KEY")
    if not key:
        pytest.skip("DART_API_KEY 미설정")
    client = DartClient(api_key=key)
    code = client.find_corp_code("삼성전자")
    assert code is not None
    rows = client.list_disclosures(code, "20250101", "20251231")
    assert isinstance(rows, list)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_dart.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.tools'`

- [ ] **Step 3: `tools/dart.py` 구현**

```python
"""DART OpenAPI 클라이언트와 리서처용 툴.

API 키는 절대 예외 메시지나 로그에 담지 않는다.
"""

from __future__ import annotations

import io
import json
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import httpx
from anthropic import beta_tool

_BASE = "https://opendart.fss.or.kr/api"
_CACHE = Path.home() / ".cache" / "dpic" / "corp_codes.json"

#: 조회 결과 없음. 에러가 아니라 빈 결과다.
_STATUS_NO_DATA = "013"
_STATUS_OK = "000"


class DartError(Exception):
    """DART가 비정상 status를 반환했을 때. 메시지에 API 키를 담지 않는다."""


class DartClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=30.0)

    def _get_json(self, path: str, **params: str) -> dict:
        response = self._http.get(
            f"{_BASE}/{path}", params={"crtfc_key": self._key, **params}
        )
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status == _STATUS_NO_DATA:
            return {}
        if status != _STATUS_OK:
            # payload["message"]만 담는다. params에는 키가 들어 있으므로 쓰지 않는다
            raise DartError(f"DART status {status}: {payload.get('message', '')}")
        return payload

    def find_corp_code(self, company_name: str) -> str | None:
        """회사명으로 8자리 고유번호를 찾는다. 전체 목록은 로컬에 캐시한다."""
        table = self._corp_code_table()
        exact = table.get(company_name)
        if exact:
            return exact
        for name, code in table.items():
            if company_name in name:
                return code
        return None

    def _corp_code_table(self) -> dict[str, str]:
        if _CACHE.exists():
            return json.loads(_CACHE.read_text(encoding="utf-8"))

        response = self._http.get(
            f"{_BASE}/corpCode.xml", params={"crtfc_key": self._key}
        )
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            xml_bytes = archive.read(archive.namelist()[0])

        table: dict[str, str] = {}
        for item in ET.fromstring(xml_bytes).iter("list"):
            name = (item.findtext("corp_name") or "").strip()
            code = (item.findtext("corp_code") or "").strip()
            if name and code:
                table[name] = code

        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
        return table

    def list_disclosures(
        self, corp_code: str, begin: str, end: str, kind: str | None = None
    ) -> list[dict]:
        params = {
            "corp_code": corp_code,
            "bgn_de": begin,
            "end_de": end,
            "page_count": "100",
        }
        if kind:
            params["pblntf_ty"] = kind
        return self._get_json("list.json", **params).get("list", [])

    def fetch_document(self, rcept_no: str) -> str:
        """공시 원문(zip 안의 XML)을 텍스트로 반환한다."""
        response = self._http.get(
            f"{_BASE}/document.xml",
            params={"crtfc_key": self._key, "rcept_no": rcept_no},
        )
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            raw = archive.read(archive.namelist()[0])
        return raw.decode("utf-8", errors="replace")


def _shared_client() -> DartClient:
    key = os.environ.get("DART_API_KEY")
    if not key:
        raise DartError("DART_API_KEY 환경변수가 설정되지 않았다")
    return DartClient(api_key=key)


@beta_tool
def dart_search(company_name: str, keyword: str) -> str:
    """DART 공시에서 기업의 특정 주제 관련 내용을 찾는다.

    감사보고서 주석의 수주잔고·계약부채·무형자산·산업재산권, 기술성 평가 관련
    서류를 확인할 때 쓴다. 비상장 기업은 공시 의무가 없어 결과가 없을 수 있다.

    Args:
        company_name: 회사명. 정확한 법인명일수록 좋다.
        keyword: 찾고자 하는 주제 (예: "산업재산권", "수주잔고", "기술성 평가").
    """
    client = _shared_client()
    corp_code = client.find_corp_code(company_name)
    if corp_code is None:
        return f"DART에서 '{company_name}'을(를) 찾지 못했다. 비상장이라 공시 의무가 없을 수 있다."

    rows = client.list_disclosures(corp_code, "20220101", "20261231")
    if not rows:
        return f"'{company_name}'(고유번호 {corp_code})의 공시가 없다."

    hits: list[str] = []
    for row in rows[:20]:
        text = client.fetch_document(row["rcept_no"])
        if keyword not in text:
            continue
        index = text.index(keyword)
        excerpt = text[max(0, index - 400) : index + 400]
        hits.append(
            f"[{row['rcept_dt']}] {row['report_nm']} (접수번호 {row['rcept_no']})\n{excerpt}"
        )
        if len(hits) >= 5:
            break

    if not hits:
        return f"'{company_name}'의 최근 공시 {len(rows)}건에서 '{keyword}'를 찾지 못했다."
    return "\n\n---\n\n".join(hits)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_dart.py -v`
Expected: PASS (4 passed, 1 deselected — live 마커)

- [ ] **Step 5: 실제 DART 연결 확인**

Run: `python -m pytest tests/test_dart.py -m live -v`
Expected: PASS. 실패하면 `.env`의 `DART_API_KEY`를 확인한다. **키 값을 터미널에 출력하지 말 것.**

DART 엔드포인트 응답 형식이 문서와 다르면 이 단계에서 드러난다. 다르면 `_get_json`과 `list_disclosures`를 실제 응답에 맞춰 고치고 Step 4의 목 테스트도 함께 갱신한다.

- [ ] **Step 6: 커밋**

```bash
git add agents/proven_scalability/tools tests/test_dart.py
git commit -m "feat(tools): DART OpenAPI 클라이언트와 dart_search 툴 추가"
```

---

### Task 5: KIPRIS 자리와 웹 검색 툴

**Files:**
- Create: `agents/proven_scalability/tools/kipris.py`
- Create: `agents/proven_scalability/tools/web.py`
- Test: `tests/test_kipris.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `kipris.KiprisUnavailable(Exception)`
  - `kipris.patent_search(applicant: str) -> str` — `@beta_tool`. 키 미확보 상태에서는 한계를 설명하는 문자열을 반환한다
  - `web.WEB_SEARCH_TOOL: dict` — 서버 툴 정의 `{"type": "web_search_20260209", "name": "web_search"}`

KIPRIS 키가 없으므로 실제 조회를 하지 않는다. **조용히 빈 결과를 주지 않고, 확인 불가라는 사실을 리서처에게 명시적으로 알린다** — 그래야 리서처가 `B2`를 `UNVERIFIABLE`로 기록하고 실사 질문으로 넘어간다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_kipris.py`:

```python
from agents.proven_scalability.tools import kipris
from agents.proven_scalability.tools.web import WEB_SEARCH_TOOL


def test_patent_search_reports_unavailability_explicitly():
    result = kipris.patent_search.run(applicant="테스트기업")
    assert "KIPRIS" in result
    # 리서처가 UNVERIFIABLE로 기록하도록 유도하는 문구가 있어야 한다
    assert "확인" in result


def test_patent_search_does_not_claim_zero_patents():
    # "특허 0건"으로 오해될 문구가 있으면 NOT_MET으로 잘못 기록된다
    result = kipris.patent_search.run(applicant="테스트기업")
    assert "0건" not in result
    assert "없습니다" not in result


def test_web_search_tool_uses_current_type():
    assert WEB_SEARCH_TOOL["type"] == "web_search_20260209"
    assert WEB_SEARCH_TOOL["name"] == "web_search"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_kipris.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.tools.kipris'`

- [ ] **Step 3: `tools/kipris.py` 구현**

```python
"""KIPRIS 특허 조회 — 인터페이스만 정의되어 있다.

API 키를 확보하지 못했다. 키가 생기면 `patent_search` 본문을 실제 조회로 교체하고
`KiprisClient`를 이 파일에 추가한다. 그때까지 등록 특허 건수와 청구항 구조는
공개 소스로 판정할 수 없으므로, 리서처에게 '확인 불가'임을 명시적으로 알린다.
"""

from __future__ import annotations

from anthropic import beta_tool

_UNAVAILABLE = (
    "KIPRIS API 키가 확보되지 않아 특허 등록 건수와 청구항 구조를 조회할 수 없다. "
    "이 항목은 '확인 불가(UNVERIFIABLE)'로 기록하고 실사 질문으로 넘길 것. "
    "다만 DART 감사보고서의 무형자산·산업재산권 주석이나 웹 검색으로 "
    "간접 근거를 찾을 수 있다면 그것으로 기록해도 된다."
)


class KiprisUnavailable(Exception):
    """KIPRIS 키가 없거나 조회에 실패했을 때."""


@beta_tool
def patent_search(applicant: str) -> str:
    """출원인 이름으로 등록 특허를 조회한다.

    Args:
        applicant: 출원인(법인) 이름.
    """
    return _UNAVAILABLE
```

- [ ] **Step 4: `tools/web.py` 구현**

```python
"""웹 검색 서버 툴 정의.

Anthropic 서버에서 실행되므로 클라이언트 구현이 없다. Tool Runner의 tools 배열에
그대로 넣으면 된다. `_20260209` 버전은 동적 필터링이 내장되어 있으므로
code_execution 툴을 따로 선언하지 않는다.
"""

from __future__ import annotations

WEB_SEARCH_TOOL: dict = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 12,
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_kipris.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 커밋**

```bash
git add agents/proven_scalability/tools/kipris.py agents/proven_scalability/tools/web.py tests/test_kipris.py
git commit -m "feat(tools): KIPRIS 인터페이스 스텁과 웹 검색 서버 툴 정의 추가"
```

---

### Task 6: 프롬프트

**Files:**
- Create: `agents/proven_scalability/prompts.py`
- Test: `tests/test_prompts.py`

**Interfaces:**
- Consumes: `criteria.Criterion`, `criteria.criteria_for`, `schema.Calibration`
- Produces:
  - `research_prompt(block: Block, company: str, calibration: Calibration) -> str`
  - `EXTRACTION_SYSTEM: str`
  - `extraction_prompt(block: Block, transcript: str) -> str`

프롬프트는 **판정하지 말라**고 명시한다. 리서처가 점수를 세기 시작하면 설계 전제가 무너진다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_prompts.py`:

```python
from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.prompts import (
    EXTRACTION_SYSTEM,
    extraction_prompt,
    research_prompt,
)


def test_research_prompt_lists_only_its_own_block():
    prompt = research_prompt("A", "테스트기업", resolve_thresholds("materials", None))
    assert "A1_poc_reproducibility" in prompt
    assert "B1_exchange_tech_grade" not in prompt  # 블록 오염 방지
    assert "C1_capacity_plan" not in prompt


def test_research_prompt_uses_injected_thresholds():
    cal = resolve_thresholds("software_ai_robotics", None)
    prompt = research_prompt("A", "테스트기업", cal)
    assert cal.thresholds["A3_field_operation_hours"] in prompt


def test_research_prompt_flags_uncalibrated_state():
    prompt = research_prompt("A", "테스트기업", resolve_thresholds(None, None))
    assert "중립" in prompt or "주입되지" in prompt


def test_research_prompt_forbids_judging():
    prompt = research_prompt("B", "테스트기업", resolve_thresholds("deep_tech", None))
    assert "점수" in prompt
    assert "세지 마" in prompt or "판정하지" in prompt


def test_extraction_system_defines_tier_scale():
    for tier in ("1급", "2급", "3급", "4급"):
        assert tier in EXTRACTION_SYSTEM


def test_extraction_prompt_embeds_transcript():
    prompt = extraction_prompt("C", "여기가 조사 전문이다")
    assert "여기가 조사 전문이다" in prompt
    assert "C1_capacity_plan" in prompt
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.prompts'`

- [ ] **Step 3: `prompts.py` 구현**

```python
"""리서처 프롬프트. 조사용과 추출용이 분리되어 있다."""

from __future__ import annotations

from agents.proven_scalability.criteria import criteria_for
from agents.proven_scalability.schema import Block, Calibration

_BLOCK_LABEL: dict[Block, str] = {
    "A": "기술 작동 증명",
    "B": "해자 (Defensibility)",
    "C": "Scale-up 준비",
}

_RESEARCH_TEMPLATE = """\
너는 pre-IPO 기업 투자 심사의 기술성 리서처다. 담당 블록은 **({block}) {block_label}**이다.

대상 기업: {company}
적용 아키타입: {archetype}{calibration_note}

## 조사할 항목

{criteria_block}

## 하는 일

각 항목에 대해 공개 자료에서 근거를 찾는다. 툴은 다음을 쓴다.

- `dart_search` — DART 공시·감사보고서 주석. 비상장은 공시 의무가 없어 결과가 없을 수 있다
- `web_search` — 제3자 인증, peer-reviewed 논문, 언론 보도
- `patent_search` — 특허 조회 (현재 키 미확보 상태)

## 하지 않는 일

- **점수를 세지 마라.** 몇 개가 충족됐는지 계산하지 마라. 그건 코드가 한다
- **게이트 통과 여부를 판정하지 마라.** 최종 결론을 내리지 마라
- **근거 없이 추정하지 마라.** 못 찾았으면 못 찾았다고 하는 것이 정답이다

## 보고

조사가 끝나면 항목별로 다음을 정리해 답한다.

- 찾은 근거의 출처(URL 또는 공시 접수번호)와 원문 인용
- 인용에 담긴 정량값 (PoC 건수·가동시간·특허 건수·인력 비중 등)
- 그 출처가 공시인지, 제3자 인증인지, 언론 보도인지, 회사 자체 발표인지
- 근거를 찾지 못한 항목은 "찾지 못함"이라고 명시
"""

_UNCALIBRATED_LINE = (
    "\n\n**주의**: PM 에이전트의 아키타입 임계치가 주입되지 않았다. "
    "아래는 하우스 원칙 원문의 중립 기준이다. 산업 특성에 맞게 임의로 완화하거나 "
    "강화하지 말고, 이 기준 그대로 조사하라."
)

EXTRACTION_SYSTEM = """\
너는 조사 기록을 구조화된 근거 목록으로 변환한다. 새로 조사하지 않고, 주어진 기록에 \
있는 내용만 사용한다.

## 상태 판정

- `MET` — 근거를 찾았고 임계치를 충족한다
- `NOT_MET` — 근거를 찾았으나 임계치에 미달한다
- `UNVERIFIABLE` — 판정할 근거를 찾지 못했다

**`UNVERIFIABLE`과 `NOT_MET`을 혼동하지 마라.** 자료를 못 찾은 것과 자료를 찾았는데 \
기준에 못 미치는 것은 전혀 다른 정보다.

## 출처 등급

- 1급 — DART 공시, 감사보고서 주석, 등록 특허 원문, 거래소 기술성 평가
- 2급 — 제3자 공인 시험성적서, 독립 인증기관, peer-reviewed 논문
- 3급 — 언론 보도, 산업 리포트
- 4급 — 회사 자체 발표, IR 자료, 홈페이지

등급은 있는 그대로 매긴다. 하위 계층 코드가 3~4급 단독 근거를 자동으로 강등하므로, \
등급을 올려 적어 도와주려 하지 마라.

## 규칙

- 한 항목에 근거가 여럿이면 Evidence를 여러 개 만든다
- `quote`는 반드시 기록에 실제로 있는 원문이어야 한다. 요약하거나 지어내지 마라
- 근거를 못 찾은 항목도 `UNVERIFIABLE`로 반드시 포함한다
"""

_EXTRACTION_TEMPLATE = """\
다음은 ({block}) 블록의 조사 기록이다.

## 대상 항목

{criteria_ids}

## 조사 기록

{transcript}

위 기록을 Evidence 목록으로 변환하라. 대상 항목 전부에 대해 최소 하나씩 만든다.
"""


def research_prompt(block: Block, company: str, calibration: Calibration) -> str:
    lines = []
    for criterion in criteria_for(block):
        threshold = calibration.thresholds[criterion.id]
        lines.append(f"### {criterion.id} — {criterion.label}\n판정 기준: {threshold}")

    return _RESEARCH_TEMPLATE.format(
        block=block,
        block_label=_BLOCK_LABEL[block],
        company=company,
        archetype=calibration.archetype,
        calibration_note="" if calibration.injected else _UNCALIBRATED_LINE,
        criteria_block="\n\n".join(lines),
    )


def extraction_prompt(block: Block, transcript: str) -> str:
    return _EXTRACTION_TEMPLATE.format(
        block=block,
        criteria_ids="\n".join(
            f"- `{c.id}` — {c.label}" for c in criteria_for(block)
        ),
        transcript=transcript,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 커밋**

```bash
git add agents/proven_scalability/prompts.py tests/test_prompts.py
git commit -m "feat(prompts): 블록별 조사 프롬프트와 Evidence 추출 프롬프트 추가"
```

---

### Task 7: 리서처 (조사 → 추출 2단계)

**Files:**
- Create: `agents/proven_scalability/researcher.py`
- Test: `tests/test_researcher.py`

**Interfaces:**
- Consumes: `prompts.research_prompt`, `prompts.extraction_prompt`, `prompts.EXTRACTION_SYSTEM`, `tools.dart.dart_search`, `tools.kipris.patent_search`, `tools.web.WEB_SEARCH_TOOL`, `schema.Evidence`
- Produces:
  - `MODEL: str = "claude-opus-5"`
  - `EvidenceList(BaseModel)` — `items: list[Evidence]` (구조화 출력용 래퍼)
  - `RefusalError(Exception)`
  - `research_block(client, block, company, calibration, max_iterations=12) -> str` — 조사 전문
  - `extract_evidence(client, block, transcript) -> list[Evidence]`
  - `run_block(client, block, company, calibration) -> list[Evidence]` — 두 단계를 이어 붙인 것

**구현 노트**
- Tool Runner는 `client.beta.messages.tool_runner(...)`. 반환값을 순회하며 각 메시지를 확인한다
- 서버툴(웹 검색)이 붙어 있으므로 `stop_reason == "pause_turn"`이 나올 수 있다. Python Tool Runner는 이를 자동 재개하지 않으므로 **명시적으로 재시작**해야 한다
- 구조화 출력은 `client.messages.parse(..., output_format=EvidenceList)` → `response.parsed_output`
- Claude Opus 5는 거부(`stop_reason == "refusal"`)를 반환할 수 있다. `content`를 읽기 전에 확인한다
- `thinking`을 명시하지 않는다 (Opus 5 기본 adaptive)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_researcher.py` — API를 호출하지 않고 클라이언트를 대역으로 세운다:

```python
from types import SimpleNamespace

import pytest

from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.researcher import (
    MODEL,
    EvidenceList,
    RefusalError,
    extract_evidence,
    research_block,
)
from agents.proven_scalability.schema import Evidence

CAL = resolve_thresholds("materials", None)


def _msg(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason
    )


class FakeRunner:
    def __init__(self, messages):
        self._messages = messages
        self.pushed = []

    def __iter__(self):
        return iter(self._messages)

    def push_messages(self, message):
        self.pushed.append(message)


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
                outer.runner_calls.append(kwargs)
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
    runner = FakeRunner([_msg("중간까지", stop_reason="pause_turn"), _msg("마무리")])
    client = FakeClient(runner=runner)
    research_block(client, "A", "테스트기업", CAL)
    assert runner.pushed, "pause_turn이면 assistant 턴을 되밀어 재개해야 한다"


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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_researcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.researcher'`

- [ ] **Step 3: `researcher.py` 구현**

```python
"""블록별 리서처. 조사(Tool Runner)와 추출(구조화 출력)을 분리한다.

조사 중에는 자유롭게 탐색하되, 경계에서 Evidence 스키마로 타입을 강제한다.
"""

from __future__ import annotations

from pydantic import BaseModel

from agents.proven_scalability.prompts import (
    EXTRACTION_SYSTEM,
    extraction_prompt,
    research_prompt,
)
from agents.proven_scalability.schema import Block, Calibration, Evidence
from agents.proven_scalability.tools.dart import dart_search
from agents.proven_scalability.tools.kipris import patent_search
from agents.proven_scalability.tools.web import WEB_SEARCH_TOOL

MODEL = "claude-opus-5"
_MAX_TOKENS = 16000
_MAX_RESTARTS = 3


class RefusalError(Exception):
    """모델이 요청을 거부했을 때 (stop_reason == "refusal")."""


class EvidenceList(BaseModel):
    """구조화 출력용 래퍼. 최상위가 객체여야 하므로 리스트를 감싼다."""

    items: list[Evidence]


def _text_of(message) -> str:
    return "\n".join(b.text for b in message.content if b.type == "text")


def research_block(
    client,
    block: Block,
    company: str,
    calibration: Calibration,
    max_iterations: int = 12,
) -> str:
    """1단계 — 툴을 써서 조사한다. 판정하지 않고 조사 전문을 문자열로 돌려준다."""
    messages = [
        {"role": "user", "content": research_prompt(block, company, calibration)}
    ]
    parts: list[str] = []

    for _ in range(_MAX_RESTARTS):
        runner = client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=_MAX_TOKENS,
            tools=[dart_search, patent_search, WEB_SEARCH_TOOL],
            messages=messages,
            max_iterations=max_iterations,
        )
        last = None
        for message in runner:
            if message.stop_reason == "refusal":
                raise RefusalError(f"({block}) 블록 조사가 거부됐다")
            parts.append(_text_of(message))
            last = message

        if last is None or last.stop_reason != "pause_turn":
            break
        # 서버툴이 반복 한도에 걸렸다. paused 턴을 되밀어 같은 러너에서 재개한다
        runner.push_messages({"role": "assistant", "content": last.content})
        messages.append({"role": "assistant", "content": last.content})

    return "\n\n".join(p for p in parts if p.strip())


def extract_evidence(client, block: Block, transcript: str) -> list[Evidence]:
    """2단계 — 조사 전문을 Evidence 스키마로 캐스팅한다. 툴 없음, 새 조사 없음."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=_MAX_TOKENS,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": extraction_prompt(block, transcript)}],
        output_format=EvidenceList,
    )
    if response.stop_reason == "refusal":
        raise RefusalError(f"({block}) 블록 추출이 거부됐다")
    parsed = response.parsed_output
    return list(parsed.items) if parsed else []


def run_block(
    client, block: Block, company: str, calibration: Calibration
) -> list[Evidence]:
    transcript = research_block(client, block, company, calibration)
    if not transcript.strip():
        return []
    return extract_evidence(client, block, transcript)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_researcher.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add agents/proven_scalability/researcher.py tests/test_researcher.py
git commit -m "feat(researcher): 조사(Tool Runner)와 추출(구조화 출력) 2단계 리서처 추가"
```

---

### Task 8: 오케스트레이션과 CLI

**Files:**
- Create: `agents/proven_scalability/agent.py`
- Create: `agents/proven_scalability/__main__.py`
- Create: `README.md`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `researcher.run_block`, `scoring.score`, `criteria.resolve_thresholds`
- Produces:
  - `evaluate(company: str, archetype: str | None = None, thresholds: dict[str, str] | None = None, client=None) -> ProvenScalabilityResult`
  - CLI: `python -m agents.proven_scalability --company "..." [--archetype ...] [--json]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_agent.py`:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.proven_scalability.agent'`

- [ ] **Step 3: `agent.py` 구현**

```python
"""Proven Scalability 에이전트의 진입점."""

from __future__ import annotations

import anthropic
from dotenv import load_dotenv

from agents.proven_scalability.criteria import resolve_thresholds
from agents.proven_scalability.researcher import run_block
from agents.proven_scalability.schema import Block, Evidence, ProvenScalabilityResult
from agents.proven_scalability.scoring import score

_BLOCKS: tuple[Block, ...] = ("A", "B", "C")


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
    load_dotenv()
    client = client or anthropic.Anthropic()
    calibration = resolve_thresholds(archetype, thresholds)

    evidence: list[Evidence] = []
    for block in _BLOCKS:
        evidence.extend(run_block(client, block, company, calibration))

    return score(evidence, calibration)
```

- [ ] **Step 4: `__main__.py` 구현**

```python
"""CLI: python -m agents.proven_scalability --company "기업명" """

from __future__ import annotations

import argparse
import sys

from agents.proven_scalability.agent import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="proven-scalability",
        description="pre-IPO 기업의 하우스 원칙 (d) 기술성 25점을 판정한다",
    )
    parser.add_argument("--company", required=True, help="대상 기업명")
    parser.add_argument(
        "--archetype",
        default=None,
        help="PM 에이전트가 내려준 아키타입. 생략하면 uncalibrated로 실행된다",
    )
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args()

    result = evaluate(args.company, archetype=args.archetype)

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    print(f"\n{args.company} — Proven Scalability (기술성)")
    print(f"  verdict : {result.verdict}")
    print(f"  점수    : {result.score}/25 (A {result.block_scores.a}/12 · "
          f"B {result.block_scores.b}/8 · C {result.block_scores.c}/5)")
    print(f"  게이트  : {'통과' if not result.gate_failed else f'미충족 {result.gate_failed}'}")
    print(f"  커버리지: {result.evidence_coverage:.0%}")
    print(f"  보정    : {result.calibration.archetype}"
          f"{'' if result.calibration.injected else ' (미보정)'}")
    if result.calibration.note:
        print(f"  주의    : {result.calibration.note}")

    if result.diligence_questions:
        print("\n실사에서 확인할 것:")
        for question in result.diligence_questions:
            print(f"  - {question}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_agent.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 전체 테스트 확인**

Run: `python -m pytest -v`
Expected: PASS (54 passed, 1 deselected)

- [ ] **Step 7: 실제 기업으로 1회 실행**

Run: `python -m agents.proven_scalability --company "심텍"`

확인할 것 — 통과 기준은 "점수가 그럴듯한가"가 아니다:
- 크래시 없이 완주하는가
- `verdict`·`score`·`커버리지`가 모두 출력되는가
- 실사 질문 리스트가 나오는가 (KIPRIS 부재 때문에 `B2`는 거의 확실히 여기 있어야 한다)
- 아키타입을 안 줬으므로 `(미보정)`이 표시되는가

**점수의 타당성은 이 단계에서 검증하지 않는다.** 사용자가 아는 기업으로 돌려보고 근거가 말이 되는지 직접 확인해야 한다.

- [ ] **Step 8: `README.md` 작성**

```markdown
# Proven Scalability 에이전트

pre-IPO 투자 검토 멀티 에이전트의 기술성 축 (25점).

## 설계

- 설계 문서: `docs/specs/2026-08-12-proven-scalability-agent-design.md`
- 구현 계획: `docs/plans/2026-08-12-proven-scalability-agent.md`

증거 수집은 LLM이, 배점과 게이트 판정은 순수 Python이 한다. 같은 증거면 항상 같은 점수가 나온다.

## 설치

\`\`\`bash
pip install -e ".[dev]"
cp .env.example .env   # DART_API_KEY, ANTHROPIC_API_KEY 를 채운다
\`\`\`

## 실행

\`\`\`bash
python -m agents.proven_scalability --company "기업명" --archetype materials
python -m agents.proven_scalability --company "기업명" --json
\`\`\`

`--archetype`은 PM 에이전트가 내려주는 값이다. 생략하면 아키타입 중립 기준으로 실행되고
결과에 `uncalibrated`로 표시된다 — 이 에이전트는 아키타입을 자체 분류하지 않는다.

아키타입: `deep_tech` · `materials` · `industrial_hardware` · `energy_infra` · `recycling` · `software_ai_robotics`

## 테스트

\`\`\`bash
python -m pytest              # 네트워크 없이 전부 실행
python -m pytest -m live      # DART 실연결 테스트
\`\`\`

## 한계

- **KIPRIS 키 미확보** — 등록 특허 건수와 청구항 구조를 조회할 수 없어 `B2_registered_patents`는
  대부분 `UNVERIFIABLE`로 떨어진다. `tools/kipris.py`에 자리를 비워 뒀다
- **(C) Scale-up 기준은 본 설계의 제안** — 하우스 원칙 원문에 세부 기준이 없어 직접 정의했다. 팀 승인 필요
- **`INSUFFICIENT_EVIDENCE`** — 상위 오케스트레이터가 세 값을 받아줄 수 있는지 미확인
\`\`\`

- [ ] **Step 9: 커밋과 push**

```bash
git add agents/proven_scalability/agent.py agents/proven_scalability/__main__.py README.md tests/test_agent.py
git commit -m "feat(agent): 3블록 오케스트레이션과 CLI 추가"
git push -u origin Proven-Scalability-agent
```

- [ ] **Step 10: PR 생성**

```bash
gh pr create --base main --head Proven-Scalability-agent \
  --title "Proven Scalability 에이전트 (하우스 원칙 d · 기술성 25점)" \
  --body "$(cat <<'EOF'
## 무엇

하우스 투자 원칙 (d) Proven Scalability를 담당하는 하위 에이전트.
(A) 기술 작동 증명 12점 · (B) 해자 8점 · (C) Scale-up 준비 5점.

## 설계의 핵심

**증거 수집(LLM)과 배점(순수 Python)을 분리했다.** 원칙 (d)는 이미 셀 수 있는 규칙으로
쓰여 있어서 (`PoC ≥ 2회`, `석사 ≥ 60%`), 카운팅을 LLM에 맡기면 같은 기업이 돌릴 때마다
다른 점수를 받는다. `scoring.py`에는 LLM 호출이 없고, 21개 테스트로 검증된다.

**`UNVERIFIABLE`을 `NOT_MET`과 분리했다.** 근거를 못 찾은 것과 기준에 미달한 것은
다른 정보다. verdict은 게이트 미충족의 *원인*으로 갈린다.

**출처 등급 필터를 코드로 강제했다.** 원칙의 "Founder 자체 테스트만 있으면 불인정"을
프롬프트 훈계가 아니라 규칙으로 — 3~4급 근거만 있으면 `MET` 승격을 막는다.

## 검토 부탁

- (C) Scale-up 5점 기준은 원칙 원문에 없어 제가 정의했습니다 (`criteria.py`의 C1~C3). 승인 필요
- `INSUFFICIENT_EVIDENCE`를 오케스트레이터가 받아줄 수 있는지
- 아키타입별 특허 건수 하한 (`B2`) 미정
- KIPRIS 키 미확보 — `B2`는 대부분 실사 질문으로 넘어갑니다

설계 문서: `docs/specs/2026-08-12-proven-scalability-agent-design.md`
EOF
)"
```

---

## 남은 위험

| 위험 | 드러나는 시점 | 대응 |
|---|---|---|
| DART 엔드포인트 응답이 문서와 다름 | Task 4 Step 5 | 실제 응답에 맞춰 `_get_json` 수정 + 목 테스트 갱신 |
| Tool Runner의 `push_messages` 메서드명이 다름 | Task 7 Step 4 | `dir(runner)`로 확인 후 수정. Python SDK는 `pause_turn` 자동 재개를 하지 않으므로 재시작 로직 자체는 필요하다 |
| `messages.parse`가 중첩 `Evidence` 리스트를 거부 | Task 7 Step 4 | `output_config.format`에 raw JSON schema를 직접 넘기는 방식으로 대체 |
| 리서처가 프롬프트를 무시하고 점수를 셈 | Task 8 Step 7 | 무해하다 — `scoring.py`가 상태만 읽고 리서처의 결론은 버린다 |
| 웹 검색이 3~4급 근거만 물어옴 | Task 8 Step 7 | 설계대로 동작하는 것이다. 커버리지가 낮게 나오고 실사 질문이 길어진다 |
