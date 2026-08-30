# dpic_camp · 양양 5조 Pre-IPO 투자심사 에이전트

드림인베스터클럽 캠프 5조.
기업명 하나를 넣으면 우리 하우스 투자철학(a/b/c/d)에 따라 근거를 모으고, 채점하고, IC용 투자보고서를 쓴다.

> 우리는 임팩트에 투자하지만, 임팩트라는 이유로 투자하지 않습니다.
> 구조적 수요 · 검증된 기술 · 고객 손익 · 측정 가능한 임팩트가 만나는 지점에만 투자합니다.

**Claude Code 위에서 돈다. LLM API 키가 필요 없다** — 각자 자기 Claude Code 구독으로 실행한다.

---

## 시작하기 (조원용, 3분)

```bash
git clone https://github.com/dylancho/dpic_camp.git
cd dpic_camp

npm install              # 오케스트레이터 · 근거수집 · 채점 (TypeScript)
pip install -e ".[dev]"  # 원칙 d 채점기 (조원 D, Python)

# DART 키 넣기 (무료, 5분)
cp .env.example .env.local
# → .env.local 의 DART_API_KEY= 에 발급받은 키를 붙여넣는다
```

DART 키는 [opendart.fss.or.kr](https://opendart.fss.or.kr) 에서 **개인회원**으로 가입하면 즉시 나온다.
가입 폼의 "확인 URL"은 아무거나 넣어도 된다 (`http://localhost:3000`). 도메인 제한이 없다.

그다음 이 폴더에서 **Claude Code를 새로 켜고** (스킬·서브에이전트는 세션 시작 시 로드된다 —
이미 켜져 있었다면 재시작해야 `/투자심사` 와 `principle-*` 에이전트가 인식된다):

```
/투자심사 에이치투
```

끝이다. 결과는 `runs/<기업명>/report.md` 에 쌓인다.

| 명령 | 하는 일 |
|---|---|
| `/투자심사 <기업명>` | 전체 파이프라인 (수집 → 캘리브레이션 → 4개 에이전트 → 채점 → 보고서) |
| `npm run collect -- "<기업명>"` | 근거 수집만 (LLM 안 씀) |
| `npm run adapt:d -- "<기업명>"` | 조원 D 파이썬 채점기 실행 + 공용 형식 변환 (LLM 안 씀) |
| `npm run score -- "<기업명>"` | 채점만 (LLM 안 씀) |
| `npm test` | 채점·게이트 엔진 테스트 10개 |
| `python -m pytest` | 조원 D 에이전트 테스트 145개 |

---

## 파이프라인

```
  /투자심사 에스오에스랩
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 0-A · 근거 수집          npm run collect               │
│   DART 감사보고서 주석 ∥ 웹검색 ∥ 사용자 제공 IR 자료        │
│   → runs/<기업>/evidence.md   (항목마다 인용 id 부여)       │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 0-B · Threshold Calibration                            │
│   아키타입 6종 중 분류 → 이 기업에 적용할 정량 임계치 확정   │
│   → runs/<기업>/calibration.json                            │
│   ※ 스코어링 전 필수. 안 하면 4명이 다른 잣대로 채점한다     │
└─────────────────────────────────────────────────────────────┘
      │
      ▼  같은 evidence.md + 같은 calibration.json 을 4명이 공유
┌──────────────┬──────────────┬──────────────┬───────────────┐
│  a 조원 A    │  b 조원 B    │  c 나        │  d 조원 D     │
│ Structural   │ Economic     │ Physical     │ Proven        │
│ Demand (30)  │ Value (25)   │ Impact (20)  │ Scalability(25)│
└──────────────┴──────────────┴──────────────┴───────────────┘
      │  Claude Code 서브에이전트 4개 병렬
      │  각자 level(이산 판정) + 원문 인용만 반환. 점수는 안 매긴다.
      │  a·b·c → runs/<기업>/findings-<원칙>.json
      │  d     → runs/<기업>/evidence-proven-scalability.json  (조사만)
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1-B · 조원 D 파이썬 채점기      npm run adapt:d        │
│   agents/proven_scalability/ (결정론, LLM 호출 없음)        │
│   A1~A3 · B1~B4 · C1~C3 항목별 MET/NOT_MET/UNVERIFIABLE    │
│   → 공용 level로 변환 → findings-proven_scalability.json    │
│   D가 모은 근거도 psa-* id로 근거 풀에 편입 (인용 유효화)   │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2 · 결정론적 채점 & Cut-off      npm run score         │
│   ① level → 점수 (Score Pad 100점)                          │
│   ② 필수조건: Proven (A)≥1·(B)≥2 미충족 → 그 원칙 0점       │
│   ③ 하드게이트: Primary Impact Unit 미정의 → 총점 무관 탈락 │
│   ④ 편중방지 Floor: 원칙별 60% 미만 → IC 특별승인 대상      │
│   ⑤ 판정구간: 60~69 Watchlist / 70~84 IC / 85+ fast-track   │
│   ★ LLM이 여기 들어오지 않는다 → 같은 근거면 항상 같은 점수 │
│   → runs/<기업>/scorecard.md                                │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
  STEP 3 · 투자보고서    →  runs/<기업>/report.md
     판단요약 / 임계치 / Score Pad / 원칙별 의견 /
     Bear case / Kill questions / 실사 체크리스트 / 근거와 한계
```

### 이 구조를 고른 이유 3가지

1. **근거를 한 번만 모아 4명이 공유한다.**
   4개 에이전트가 각자 검색하면 서로 다른 사실 위에서 점수를 매기게 되어 합산이 의미를 잃는다.
   같은 근거 풀에서 판정해야 "왜 a는 높은데 b는 낮은가"를 IC에서 설명할 수 있다.

2. **임계치를 스코어링 전에 확정한다 (STEP 0).**
   철학 문서의 "STEP 0 — 스코어링 전 필수 수행"이 이것이다. SW 기업에 "실환경 가동 1,000시간"을
   들이대면 아무도 통과 못 하고, 원천기술에 "유료 고객 5곳"을 요구하면 전부 탈락한다.

3. **점수는 코드가 매긴다. LLM은 판정만 한다.**
   에이전트는 `level`(driver 2개 확인, 해자 3개 충족)만 내고, `level → 점수` 변환과 게이트 적용은
   `lib/scoring.ts`가 한다. LLM에게 "몇 점 줄래?"라고 물으면 매번 달라져서 IC에서 방어가 안 된다.

---

## 조원별 작업 분담

4명이 서로 다른 형태로 만들었고, **각자 만든 것을 그대로 살려서** 하나의 파이프라인에 물렸다.

| 담당 | 원칙 | 배점 | 만든 것 | 파이프라인에 붙는 방식 |
|---|---|---|---|---|
| 조원 A | a. Structural Demand | 30 | `.claude/skills/structural-demand-check/` (스킬) | `principle-a` 서브에이전트가 이 스킬을 루브릭으로 읽고 level로 변환 |
| 조원 B | b. Economic Value | 25 | `.claude/skills/economic-value-check/` (스킬) | `principle-b` 서브에이전트가 동일 방식 |
| **나** | c. Physical Impact | 20 | `.claude/agents/principle-c-physical-impact.md` | 2단계 서브에이전트 (하드 게이트 분리) |
| 조원 D | d. Proven Scalability | 25 | `agents/proven_scalability/` (Python 결정론 채점기) | `principle-d`가 **조사만** 하고, 채점은 파이썬이. `npm run adapt:d`가 변환 |
| **나** | 오케스트레이션 | — | `.claude/skills/투자심사/`, `lib/`, `scripts/` | 전체 조립 |

**각자 자기 파일만 고치면 된다.** 서로 충돌하지 않는다.
A·B는 `SKILL.md`의 판정 기준을, D는 파이썬 `criteria.py`/`scoring.py`를 고치면
`/투자심사`를 다시 돌릴 때 바로 반영된다.

### 형식이 다른 셋을 어떻게 합쳤나

| 문제 | 해결 |
|---|---|
| A·B의 스킬은 `PASS/CONDITIONAL PASS/FAIL` 서사를 내고, 채점 엔진은 `level`을 원한다 | 각 서브에이전트 파일에 **매핑표**를 박았다. (예: Policy Dependency `Mostly Yes` → `sd.subsidy` level 2). 스킬 원문은 손대지 않았다 |
| D는 Python이고 자체 채점기(A 12·B 8·C 5 = 25점)를 갖는다 | 배점이 우리 Score Pad와 정확히 같아서, **D의 채점기를 버리지 않고** `resolved_statuses`의 MET 개수를 level로 옮겼다 (`scripts/adapt-proven.mts`) |
| 조원들이 새로 찾은 근거를 인용하면 "없는 sourceId"로 버려진다 | `extraEvidence` 필드를 계약서에 추가. 채점 직전에 근거 풀로 편입한다. D의 근거는 `psa-*` id로 편입 |
| level만 남으면 IC에서 설명이 안 된다 | `skillReport` 필드로 조원들이 정의한 표·서사 전문을 실어 보고서 본문에 그대로 쓴다 |

### 4명이 반드시 지켜야 하는 규칙 3가지

이게 깨지면 에이전트를 아무리 잘 써도 점수가 의미 없어진다. 각 에이전트 파일 상단에 박혀 있다.

1. **점수를 매기지 않는다.** `level`만 낸다.
2. **모든 판정에 원문 인용을 붙인다.** `evidence[].sourceId`가 `evidence.md`에 없으면
   `npm run score`가 **자동으로 버린다** (환각 인용 방어). 인용 없는 판정은 근거 없는 점수다.
3. **모르면 `unknown`.** 사전지식으로 사실을 만들어내면 실격. `missingData`에 무엇이 없었는지 적는다.

`npm run score`는 Zod로 형식을 검증한다. 스키마를 어기면 "제출 문제"로 콘솔에 찍히니 그때 고치면 된다.

### 원칙 c가 2단계인 이유

`physical_impact`만 **하드 게이트**를 갖는다 — Primary Impact Unit이 정의 안 되면 총점 무관 탈락.
한 번에 물으면 모델이 "탄소를 줄입니다" 같은 서사를 물리 단위로 착각해 게이트를 통과시켜 버려서,
STEP c-1(단위 확정)과 c-2(스코어링)를 분리했다. 다른 원칙도 필요하면 같은 식으로 쪼개면 된다.

---

## 파일 지도

```
.claude/
  skills/
    투자심사/SKILL.md            ★ 오케스트레이터 (STEP 0~3)
    structural-demand-check/     조원 A의 원칙 a 루브릭
    economic-value-check/        조원 B의 원칙 b 루브릭
  agents/principle-a~d-*.md      원칙별 서브에이전트 4개
lib/
  philosophy.ts                  철학 원문 + Score Pad 루브릭 (단일 진실 원천)
  archetypes.ts                  STEP 0 아키타입 6종
  contract.ts                    조원 간 계약서 (Zod 스키마)
  scoring.ts                     결정론적 채점 + Cut-off (LLM 없음)
  run-store.ts                   runs/<기업>/ 디렉터리 규약
  evidence/  pack.ts dart.ts web.ts zip.ts
agents/proven_scalability/       조원 D의 원칙 d 채점기 (Python, 결정론)
  criteria.py scoring.py schema.py
  extractors/dart_rules.py       DART 공시 규칙 추출
  tools/dart.py tools/kipris.py
docs/agent-instructions/         조원 D의 조사 지시서 (principle-d가 따른다)
scripts/
  collect.mts                    근거 수집
  adapt-proven.mts               조원 D 채점기 → 공용 형식 어댑터
  score.mts                      채점
  scoring.test.ts                Cut-off 규칙 10개 테스트
tests/                           조원 D 테스트 145개 (pytest)
runs/<기업>/                     심사 1건의 모든 산출물 (gitignore)
app/                             (선택) 웹 UI 버전 — API 키가 있을 때만 동작
```

---

## 팀

드림인베스터클럽 캠프 5조.

- [@dylancho](https://github.com/dylancho)
- [@xavierchoi](https://github.com/xavierchoi)
- [@ppaxen](https://github.com/ppaxen)
- [@bananawooyou-invest](https://github.com/bananawooyou-invest)
- [@eunjaekim50](https://github.com/eunjaekim50)

---

## 알아둘 것

- **근거가 없으면 점수가 낮게 나온다. 이건 버그가 아니라 설계다.** 우리 철학은 근거 없는 임팩트를
  서사로 간주한다. 낮은 점수가 나오면 `runs/<기업>/scorecard.md`의 "미확인 데이터"를 보고
  IR 자료를 `evidence.md`에 붙여넣은 뒤 다시 돌리면 된다.
- **첫 DART 호출은 10~20초 걸린다.** 전체 기업 고유번호(약 20MB)를 받아 캐싱한다. 두 번째부터 빠르다.
- **`TAVILY_API_KEY`는 선택이다.** 없으면 오케스트레이터가 Claude Code 내장 WebSearch로 보완한다.
  있으면 수집이 더 촘촘해진다 ([tavily.com](https://tavily.com), 무료 1,000건/월).
- **한글 상호와 영문 표기가 다르면 별칭을 줘라.** 웹 검색 관련성 필터가 기업명 직접 언급을 요구하기
  때문에, 영문 기사가 통째로 걸러질 수 있다.
  `npm run collect -- "에이치투" "" "H2 Inc"` 처럼 3번째 이후 인자로 넘긴다.
  필터가 근거를 너무 많이 지우면(3건 미만) 제외분을 `web-unverified-*` 로 되살리되
  "관련성 미확인" 표시를 달아준다 — **인용 전에 그 항목이 정말 대상 기업 자료인지 직접 확인해야 한다.**
- **`app/` 웹 UI 버전도 남아 있다.** 배포용이 필요하면 `AI_GATEWAY_API_KEY`(유료 크레딧 필요)를
  넣고 `npm run dev`. 해커톤 시연은 Claude Code 쪽이 비용 0원이라 더 편하다.
- **이 저장소는 public이다.** `.env.local`은 gitignore되어 있지만, DART 키를 코드에 하드코딩하지 말 것.
