# Proven Scalability 에이전트

pre-IPO 투자 검토 멀티 에이전트의 기술성 축 (25점).

**이 레포의 파이썬 코드는 어떤 LLM API도 호출하지 않는다.** `anthropic` 등 LLM SDK를
import하지 않는다는 사실을 `tests/test_no_llm_dependency.py`가 레포 전체를 훑어 강제한다.
채점(`scoring.py`)은 순수 결정론적 코드다 — 같은 증거를 넣으면 항상 같은 점수가 나온다.
조사(증거 수집)만 사람이 직접 자신의 LLM 세션에서 수행하고, 그 결과를 파일로 저장해
넘긴다.

## 설계

- 설계 문서: `docs/specs/2026-08-12-proven-scalability-agent-design.md`
- 구현 계획: `docs/plans/2026-08-12-proven-scalability-agent.md`, `docs/plans/2026-08-13-no-model-call-pivot.md`

## 설치

```bash
pip install -e ".[dev]"
cp .env.example .env   # DART_API_KEY 를 채운다 (선택 — 없어도 증거 파일만으로 동작한다)
```

`ANTHROPIC_API_KEY`는 필요 없다. 필요한 비밀값은 `DART_API_KEY` 하나뿐이고, 그마저도
없으면 DART 자동 추출 없이 증거 파일만으로 채점이 계속된다.

## 증거는 두 갈래로 들어온다 — 둘 다 불완전하다

이 에이전트는 스스로 조사하지 않는다. 판정 항목 10개에 대한 증거는 아래 두 경로로만
채점기에 들어가고, **어느 쪽도 혼자서는 완전하지 않다.**

| 경로 | 무엇을 하는가 | 커버리지 |
|---|---|---|
| **DART 규칙 추출** (`extractors/dart_rules.py`) | DART 공시 원문을 결정론적 정규식으로 훑어 Evidence를 뽑는다. 사람 개입 없음, 실행할 때마다 자동 | `B2_registered_patents`·`B3_domain_expertise` **2개 항목만**. 나머지 8개는 규칙 자체가 없다 |
| **`.md` 지시서 + 사용자의 LLM** (`docs/agent-instructions/`) | 레포에는 조사 지시서(Markdown)만 있다. 사람이 그걸 자기 LLM 세션(Claude, ChatGPT 등 아무 제품이나)에 붙여넣어 조사시키고, 결과를 `evidence.json`으로 저장한다 | 나머지 8개 항목(A1~A3, B1, B4, C1~C3) 포함 최대 10개. 단 사람이 실제로 이 절차를 밟았을 때만 |

**`--evidence` 없이 실행하면** DART 규칙 추출 결과만으로 채점한다. 커버하는 2개 항목을
제외한 나머지는 전부 `UNVERIFIABLE`로 남는다. **DART 키도 증거 파일도 없이 실행하면**
전 항목이 `UNVERIFIABLE`인 결과가 나온다 — 이것은 버그가 아니라 정확한 동작이다.
`research_notes`에 "증거가 하나도 입력되지 않았다 — 아무것도 조사되지 않았다"가 그대로
남아서, 커버리지 0인 결과가 "찾아봤지만 없었다"가 아니라 "애초에 조사를 안 했다"임을
구분해준다.

### 한계 — 오버셀하지 않기 위해 명시한다

- **등급 필터는 거짓말하는 출처를 잡아내지 못한다.** `scoring.py`는 3~4급 근거 단독을
  `MET`으로 승격하지 않고 `UNVERIFIABLE`로 강등한다. 하지만 이건 **출처가 스스로 밝힌
  등급을 신뢰한다는 전제** 위에서만 작동한다. 사용자의 LLM이 보도자료에서 읽은 내용에
  `source_tier: 1`을 잘못(혹은 의도적으로) 매기면, 등급 필터도 `evidence_io`도 그 거짓을
  잡아내지 못한다. `docs/agent-instructions/00-evidence-schema.md`가 등급을 부풀리지
  말라고 지시서 수준에서 명시하지만, 코드가 강제하는 안전장치는 아니다.
- **`B1_exchange_tech_grade`에는 DART 규칙이 없다.** 거래소 기술성 평가 등급("A", "BBB"
  등)은 상장 시점 증권신고서/투자설명서에만 나오는데, 사업/분기보고서 본문에서
  "기술평가"라는 단어는 기관명(예: 한국산업기술평가관리원)이나 연구과제명의 일부로만
  등장하고 등급 문자열로는 등장하지 않는다는 것을 2026-08-13 실제 공시로 확인했다.
  키워드 매칭 규칙을 만들면 확신을 갖고 틀린 답(오탐 `MET`)을 낼 위험이 이 프로젝트가
  가장 경계하는 실패 모드다. 그래서 이 항목은 규칙을 만들지 않고 `.md` 지시서(사람의
  조사)로 넘겼다 — **이건 의도된 결정이지 미구현이 아니다.** 나중에 단순 키워드 매칭으로
  "고쳐서" 채우면 안 된다.
- **(C) Scale-up 5점 기준은 이 설계의 자체 제안이다.** 하우스 투자 원칙 원문에 (C)의
  세부 기준이 없어 이 설계에서 직접 정의했다 (`docs/specs/...design.md` §7). 팀 승인 전
  임시 기준으로 취급할 것.
- **KIPRIS 키 미확보** — 등록 특허 건수·청구항 구조를 API로 조회할 수 없다.
  `B2_registered_patents`는 DART 무형자산 주석(규칙 추출)이나 사람의 조사로만 채워진다.

## 실행

```bash
python -m agents.proven_scalability --company "기업명" --archetype materials
python -m agents.proven_scalability --company "기업명" --evidence evidence.json
python -m agents.proven_scalability --company "기업명" --evidence evidence.json --json
```

| 플래그 | 필수 | 설명 |
|---|---|---|
| `--company` | 예 | 대상 기업명. DART 규칙 추출과 결과 표시에 쓰인다 |
| `--archetype` | 아니오 | PM 에이전트가 내려주는 값. 생략하면 아키타입 중립 기준으로 실행되고 결과에 `uncalibrated`로 표시된다 — 이 에이전트는 아키타입을 자체 분류하지 않는다 |
| `--evidence` | 아니오 | 사용자의 LLM 세션이 만든 증거 JSON 경로. 생략하면 DART 규칙 추출만으로 채점한다 (아래 "증거는 두 갈래로 들어온다" 참고) |
| `--json` | 아니오 | 사람이 읽는 텍스트 대신 JSON으로 출력 |

아키타입: `deep_tech` · `materials` · `industrial_hardware` · `energy_infra` · `recycling` · `software_ai_robotics`

### 증거 파일을 직접 만드는 법 (evidence.json)

DART 규칙이 다루지 못하는 8개 항목을 채우려면 사용자가 자신의 LLM 세션에서 직접
조사해야 한다. 절차는 `docs/agent-instructions/README.md`에 있고, 요약하면:

1. 자기 LLM 세션에 `docs/agent-instructions/00-evidence-schema.md`와 조사할 블록 문서
   (`01-block-a-...md` / `02-block-b-...md` / `03-block-c-...md`)를 붙여넣는다
2. "이 기업을 조사해서 evidence.json을 만들어줘"라고 시킨다
3. 결과를 `evidence.json`으로 저장한다
4. 위 명령의 `--evidence` 플래그로 넘긴다

`evidence.json`의 스키마 위반 항목(모르는 `criterion_id`, 범위 밖 `source_tier` 등)은
조용히 버려지지 않는다 — 경고로 남아 실행 결과의 조사 결함 섹션에 그대로 출력된다.

`--json`은 `evidence`(수집된 근거 원문 그대로, 필터 이전 — 감사 추적용)와
`resolved_statuses`(등급 필터·병합을 거친 항목별 최종 상태 — 점수 산출에 실제로 쓰인 값)를
둘 다 담는다. 점수와 일치해야 하는 상태를 읽으려면 `resolved_statuses`를 볼 것 —
`evidence[i].status`는 최종 판정과 다를 수 있다.

## 테스트

```bash
python -m pytest              # 네트워크 없이 전부 실행
python -m pytest -m live      # DART 실연결 테스트
```

## 그 외 한계

- **`INSUFFICIENT_EVIDENCE`** — 상위 오케스트레이터가 세 값(PASS/FAIL/INSUFFICIENT_EVIDENCE)을
  받아줄 수 있는지 미확인
