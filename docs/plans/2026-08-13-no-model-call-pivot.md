# 모델 호출 제거 — 설계 전환 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

작성 2026-08-13 · 브랜치 `Proven-Scalability-agent` · 선행: `2026-08-12-proven-scalability-agent.md`

## 왜 바뀌는가

캠프 평가 규칙상 **제출 산출물이 LLM API를 호출하면 안 된다.** 기존 구조는 `researcher.py`가
Tool Runner로 조사하고 `messages.parse`로 추출했는데, 그 층 전체가 무효다.

다만 이 설계의 중심 주장은 처음부터 "판정은 순수 파이썬이 한다"였고, LLM은 증거를 **모으는**
데만 썼다. 채점 엔진에는 모델이 한 줄도 없다. 그래서 전환은 교체가 아니라 **입력 경로의 변경**이다.

## 전환 후 구조

```
[1] DART 규칙 추출 (결정론)          [2] .md 지시서 → 사용자의 LLM
    공시 원문을 키워드·정규식으로        레포에 md만 올림. 사용자가 자기 LLM
    훑어 Evidence 초안 생성             세션에서 읽고 조사 → Evidence JSON 저장
              \                              /
               \                            /
                v                          v
              [3] evidence 병합 → scoring.py (변경 없음)
                                v
                     ProvenScalabilityResult
```

레포 안의 파이썬은 **어떤 LLM API도 호출하지 않는다.** md는 데이터이지 실행 코드가 아니다.

## 살아남는 것 / 없어지는 것

| 모듈 | 처리 |
|---|---|
| `schema.py` · `criteria.py` · `scoring.py` | **그대로.** 모델 호출 없음, 테스트 그대로 |
| `tools/dart.py` | **그대로.** 순수 HTTP 클라이언트. 단 `@beta_tool` 데코레이터만 제거 |
| `tools/kipris.py` | `@beta_tool` 제거, 함수는 유지 |
| `researcher.py` | **삭제** |
| `prompts.py` | **md 지시서로 변환 후 삭제** |
| `tools/web.py` | **삭제** (Anthropic 서버툴) |
| `agent.py` | 리서처 호출 → 증거 파일 읽기 + DART 추출로 교체 |
| `__main__.py` | `--evidence` 플래그 추가 |

## Global Constraints

- **레포의 어떤 파이썬 파일도 `anthropic`을 import하지 않는다.** 테스트로 강제한다
- `scoring.py`·`criteria.py`·`schema.py`의 판정 동작을 바꾸지 않는다. 기존 테스트는 그대로 통과해야 한다
- DART 규칙 추출이 만드는 Evidence는 **출처 등급 1**이다 (공시 원문)
- 규칙이 확신할 수 없으면 Evidence를 만들지 않는다. `UNVERIFIABLE`로 남겨 실사 질문이 되게 한다.
  **추측해서 `MET`을 만들면 안 된다** — 등급 필터가 막아주지 못하는 유일한 구멍이다
- md 지시서는 특정 LLM 제품에 의존하지 않는다. Claude·GPT 등 아무 세션에서나 읽고 수행 가능해야 한다
- 비밀값은 여전히 `.env`. `DART_API_KEY`만 필요하다. `ANTHROPIC_API_KEY`는 더 이상 필요 없다

---

### Task 1: LLM 층 제거와 증거 파일 입력

**Files:**
- Delete: `agents/proven_scalability/researcher.py`, `agents/proven_scalability/prompts.py`,
  `agents/proven_scalability/tools/web.py`, `tests/test_researcher.py`, `tests/test_prompts.py`
- Modify: `agents/proven_scalability/agent.py`, `agents/proven_scalability/__main__.py`,
  `agents/proven_scalability/tools/dart.py`, `agents/proven_scalability/tools/kipris.py`,
  `tests/test_agent.py`, `tests/test_dart.py`, `tests/test_kipris.py`, `pyproject.toml`
- Create: `agents/proven_scalability/evidence_io.py`, `tests/test_evidence_io.py`,
  `tests/test_no_llm_dependency.py`

**Produces:**
- `evidence_io.load_evidence(path: Path) -> tuple[list[Evidence], list[str]]` — 증거 JSON을 읽어
  `Evidence` 리스트와 경고 리스트를 반환. 스키마 위반 항목은 버리되 경고로 남긴다
- `evidence_io.EvidenceFileError(Exception)`
- `evaluate(company, archetype=None, thresholds=None, evidence_path=None, dart_client=None)`

- [ ] **Step 1: LLM 의존성 금지 테스트를 먼저 쓴다**

`tests/test_no_llm_dependency.py` — 이 테스트가 이 전환의 핵심 계약이다:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_no_llm_dependency.py -v`
Expected: FAIL — `researcher.py imports anthropic` 외 다수

- [ ] **Step 3: LLM 층을 삭제한다**

`researcher.py`, `prompts.py`, `tools/web.py`와 대응 테스트 파일을 지운다.
`tools/dart.py`와 `tools/kipris.py`에서 `from anthropic import beta_tool`과 `@beta_tool`
데코레이터를 제거한다 — **함수 본문과 docstring은 그대로 둔다.** docstring은 이제 md 지시서가
참조하는 설명이 된다. `pyproject.toml`의 `anthropic` 의존성도 지운다.

`test_dart.py`·`test_kipris.py`에서 `@beta_tool` 객체를 전제한 호출이 있으면 평범한 함수 호출로
바꾼다.

- [ ] **Step 4: `evidence_io.py`를 만든다**

```python
"""사용자의 LLM 세션이 만든 증거 JSON을 읽어들인다.

md 지시서(`docs/agent-instructions/`)를 따라 조사한 결과가 이 형식으로 저장되고,
여기서 스키마 검증을 거쳐 채점기로 들어간다. 검증에 실패한 항목은 조용히 버리지 않고
경고로 남긴다 — 조용히 버리면 '근거 없음'과 구분되지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from agents.proven_scalability.schema import Evidence


class EvidenceFileError(Exception):
    """증거 파일을 아예 읽을 수 없을 때."""


def load_evidence(path: Path) -> tuple[list[Evidence], list[str]]:
    """증거 JSON을 읽는다. (유효한 Evidence, 경고) 를 돌려준다."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceFileError(f"증거 파일이 없다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceFileError(f"증거 파일이 올바른 JSON이 아니다: {path}") from exc

    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise EvidenceFileError(
            "증거 파일의 최상위는 리스트이거나 items 키를 가진 객체여야 한다"
        )

    evidence: list[Evidence] = []
    warnings: list[str] = []
    for index, item in enumerate(items):
        try:
            evidence.append(Evidence.model_validate(item))
        except ValidationError as exc:
            warnings.append(
                f"증거 파일 {index}번 항목을 스키마 위반으로 버렸다 "
                f"({exc.error_count()}건): {_first_error(exc)}"
            )
    return evidence, warnings


def _first_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}"
```

- [ ] **Step 5: `evidence_io` 테스트를 쓴다**

`tests/test_evidence_io.py` — 최소한 다음을 덮는다. 각 케이스는 임시 파일로 쓴다.

- 정상 파일 → `Evidence` 리스트가 나온다 (`items` 키 형태와 최상위 리스트 형태 둘 다)
- 파일 없음 → `EvidenceFileError`
- 깨진 JSON → `EvidenceFileError`
- 최상위가 숫자/문자열 → `EvidenceFileError`
- **알 수 없는 `criterion_id` → 버려지되 경고가 남는다** (조용히 사라지면 안 된다)
- `source_tier: 9` → 버려지되 경고가 남는다
- 항목 일부만 유효 → 유효한 것만 반환되고 경고 개수가 맞는다

- [ ] **Step 6: `agent.evaluate`를 재배선한다**

`run_block` 호출을 지운다. 새 시그니처:

```python
def evaluate(
    company: str,
    archetype: str | None = None,
    thresholds: dict[str, str] | None = None,
    evidence_path: Path | None = None,
    dart_client=None,
) -> ProvenScalabilityResult:
```

동작: DART 규칙 추출(Task 2)의 결과와 `evidence_path`의 결과를 합쳐 `score()`에 넘긴다.
`evidence_io`의 경고와 DART 추출의 기록은 전부 `research_notes`로 들어간다.
**둘 다 비어 있으면** `research_notes`에 "증거가 하나도 입력되지 않았다"를 남긴다 —
전 항목 `UNVERIFIABLE`이 '조사했지만 없었다'로 오해되면 안 된다.

Task 2가 아직 없으므로 이 태스크에서는 DART 추출을 빈 리스트로 두고, Task 2에서 연결한다.

- [ ] **Step 7: 전체 테스트**

Run: `python -m pytest -v`
Expected: `test_no_llm_dependency.py` 통과. `scoring`·`criteria`·`schema`·`dart`·`kipris`
테스트가 전부 그대로 통과. 삭제된 모듈의 테스트는 사라졌으므로 총계는 줄어든다.

- [ ] **Step 8: 커밋**

```bash
git add -A
git commit -m "refactor: LLM 호출 층을 걷어내고 증거 파일 입력으로 바꾼다"
```

---

### Task 2: DART 규칙 추출기

**Files:**
- Create: `agents/proven_scalability/extractors/__init__.py`,
  `agents/proven_scalability/extractors/dart_rules.py`, `tests/test_dart_rules.py`
- Modify: `agents/proven_scalability/agent.py`

**Produces:**
- `dart_rules.extract(client: DartClient, company: str) -> tuple[list[Evidence], list[str]]`
- `dart_rules.RULES: tuple[Rule, ...]`

**무엇을 뽑을 수 있고 없는가.** 이걸 정직하게 긋는 것이 이 태스크의 핵심이다.

| 항목 | DART에서 가능한가 | 규칙 |
|---|---|---|
| `B1_exchange_tech_grade` | 부분 | 기술특례상장 관련 공시에서 "기술평가" + 등급 문자열 |
| `B2_registered_patents` | 부분 | 사업보고서 "지적재산권"/"산업재산권" 표에서 특허 건수 패턴 |
| `B3_domain_expertise` | 부분 | "연구개발활동" 섹션의 학위별 인력 수 (석사·박사) |
| `A1` `A2` `A3` `B4` `C1` `C2` `C3` | **불가** | 공시에 존재하지 않는 정보다. md 지시서 담당 |

규칙이 뽑는 것은 **후보**다. 숫자를 확실히 읽었을 때만 Evidence를 만들고, 임계치 비교가
애매하면 `NOT_MET`이 아니라 아무것도 만들지 않는다 (→ `UNVERIFIABLE` 유지).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_dart_rules.py` — `DartClient`를 `httpx.MockTransport`로 대역화하고, 실제 공시
문구를 본뜬 픽스처 텍스트로 검증한다. 최소한:

- 특허 건수 표가 있는 문서 → `B2_registered_patents` Evidence, `source_tier == 1`,
  `extracted_value`에 건수
- 학위별 인력 표 → `B3_domain_expertise` Evidence, 비중이 계산됨
- 기술평가 등급 문자열 → `B1_exchange_tech_grade` Evidence
- **숫자를 못 읽는 문서 → Evidence 0개, 경고 있음** (추측 금지)
- 공시 자체가 없는 기업 → Evidence 0개, "공시 없음" 경고
- 규칙이 다루지 않는 항목(A1 등)은 **어떤 입력에도 Evidence가 생기지 않는다**

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/test_dart_rules.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현한다**

`Rule`은 `criterion_id`, 검색 키워드, 추출 정규식, 임계치 판정 함수를 갖는 dataclass로 둔다.
`extract`는 회사의 최근 공시를 훑어 각 규칙을 적용하고, 매칭된 원문 발췌를 `quote`에 담는다.
`source_url`은 DART 뷰어 URL(`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=...`)로 만든다.

임계치는 `Calibration.thresholds`가 아니라 **규칙 자체가 정한 하한**을 쓰되, 판정이 애매하면
Evidence를 만들지 않는다. 아키타입별 임계치 해석은 사람과 md 지시서의 몫이다.

- [ ] **Step 4: 통과 확인 후 `agent.evaluate`에 연결**

Task 1에서 비워둔 자리에 `dart_rules.extract`를 넣는다. `dart_client=None`이면 `.env`에서
`DART_API_KEY`를 읽어 만들고, 키가 없으면 예외 대신 경고를 남기고 DART 없이 진행한다 —
증거 파일만으로도 돌아가야 한다.

- [ ] **Step 5: 커밋**

```bash
git commit -m "feat(extractors): DART 공시 규칙 추출기 추가"
```

---

### Task 3: md 지시서

**Files:**
- Create: `docs/agent-instructions/README.md`,
  `docs/agent-instructions/00-evidence-schema.md`,
  `docs/agent-instructions/01-block-a-기술작동증명.md`,
  `docs/agent-instructions/02-block-b-해자.md`,
  `docs/agent-instructions/03-block-c-scaleup.md`
- Delete: (없음 — `prompts.py`는 Task 1에서 이미 삭제)

이 파일들이 **사용자의 LLM이 읽는 유일한 인터페이스**다. 기존 `prompts.py`의 내용을 옮기되,
파이썬 템플릿이 아니라 사람과 모델이 같이 읽는 문서로 다시 쓴다.

- [ ] **Step 1: `00-evidence-schema.md`**

출력 계약을 정의한다. `Evidence` 필드, 세 가지 상태, 네 등급, 그리고 **정확한 JSON 예시**.
10개 `criterion_id`를 표로 전부 나열한다 — 모델이 ID를 지어내면 `evidence_io`가 버리고
경고를 남기므로, 여기가 유일한 정답지다.

`UNVERIFIABLE`과 `NOT_MET`의 차이, 3~4급 단독 근거는 `MET`으로 올리지 말 것을 명시한다.

- [ ] **Step 2: 블록별 지시서 3개**

각각 자기 블록의 항목만 담는다 (교차 오염 방지). 각 항목마다:
판정 기준(원칙 원문), 아키타입별 치환, 어디서 찾는지, 무엇을 인용할지.

**"점수를 세지 마라"를 명시한다.** 채점은 `scoring.py`가 한다.

- [ ] **Step 3: `README.md` — 사용 흐름**

사용자가 실제로 하는 일을 순서대로 적는다:

```
1. 자기 LLM 세션에 00-evidence-schema.md 와 해당 블록 md 를 붙여넣는다
2. "이 기업을 조사해서 evidence.json 을 만들어줘" 라고 시킨다
3. 결과를 evidence.json 으로 저장한다
4. python -m agents.proven_scalability --company "기업명" --evidence evidence.json
```

- [ ] **Step 4: 커밋**

```bash
git commit -m "docs: 사용자 LLM이 읽는 조사 지시서 추가"
```

---

### Task 4: CLI · README · 스펙 갱신

**Files:**
- Modify: `agents/proven_scalability/__main__.py`, `README.md`,
  `docs/specs/2026-08-12-proven-scalability-agent-design.md`, `tests/test_main.py`

- [ ] **Step 1: `--evidence` 플래그**

```
python -m agents.proven_scalability --company "기업명" [--evidence evidence.json]
                                    [--archetype materials] [--json]
```

`--evidence` 없이 돌리면 DART 규칙 추출만으로 채점하고, `research_notes`에 "증거 파일 없이
실행했다 — 대부분의 항목이 확인 불가로 남는다"를 남긴다.

- [ ] **Step 2: `test_main.py` 갱신**

`--evidence` 경로가 텍스트/JSON 두 모드에서 동작하는지, 경고가 출력에 드러나는지.

- [ ] **Step 3: `README.md` 다시 쓴다**

"모델 호출 없음"을 맨 위에 명시한다. 두 갈래 증거 입력(DART 자동 / md+LLM 수동)과 그 한계.

- [ ] **Step 4: 스펙 §5 갱신**

§5의 2단계 리서처 설명을 지우고 새 구조로 대체한다. **§2.1~2.4는 그대로 둔다** — 수집과
판정의 분리, 3상태, 등급 필터, PM 주입은 전부 유효하다. 왜 바뀌었는지 한 문단을 §5 앞에 넣는다.

- [ ] **Step 5: 커밋 후 push, PR 갱신**

```bash
git push
```

---

## 남은 위험

| 위험 | 대응 |
|---|---|
| DART 규칙이 실제 공시 형식과 안 맞음 | Task 2 Step 4에서 실제 기업으로 확인. 안 맞으면 규칙과 픽스처를 함께 고친다 |
| 사용자 LLM이 지어낸 `criterion_id`를 보냄 | `evidence_io`가 버리고 경고. `00-evidence-schema.md`가 정답지 |
| 사용자 LLM이 등급을 부풀림 | 등급 필터가 3~4급 단독을 강등. 다만 1급이라고 거짓말하면 못 막는다 — 지시서에 명시하고 한계로 문서화 |
| 증거 파일 없이 돌려서 전 항목 UNVERIFIABLE | `research_notes`에 명시. 커버리지 0.0과 구분 가능 |
