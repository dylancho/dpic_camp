# 양양 5조 · Pre-IPO 투자보고서 에이전트

기업명을 입력하면 우리 하우스 투자철학(a/b/c/d)에 따라 근거를 모으고, 채점하고, IC용 투자보고서를 쓴다.

> 우리는 임팩트에 투자하지만, 임팩트라는 이유로 투자하지 않습니다.
> 구조적 수요 · 검증된 기술 · 고객 손익 · 측정 가능한 임팩트가 만나는 지점에만 투자합니다.

---

## 빠른 시작

```bash
npm install
cp .env.example .env.local     # AI_GATEWAY_API_KEY 최소 1개는 필요
npm run dev                    # http://localhost:3000
```

| 스크립트 | 하는 일 |
|---|---|
| `npm run dev` | 개발 서버 |
| `npm test` | 채점·게이트 엔진 테스트 (LLM 호출 없음, 즉시 실행) |
| `npm run typecheck` | 타입 검사 |
| `npm run build` | 프로덕션 빌드 |

환경변수는 `.env.example` 참고. `AI_GATEWAY_API_KEY`만 있으면 돌아가고,
`DART_API_KEY`·`TAVILY_API_KEY`가 있으면 근거 수집 품질이 크게 올라간다.

---

## 파이프라인

```
  기업명 입력
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 0-A · Evidence Pack 수집        lib/evidence/*         │
│   DART(감사보고서 주석) ∥ 웹검색 ∥ 사용자 붙여넣기 자료      │
│   → 하나의 공유 근거 풀 (각 항목에 인용 id 부여)             │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 0-B · Threshold Calibration     lib/agents/calibrate.ts│
│   아키타입 6종 중 분류 → 이 기업에 적용할 정량 임계치 확정   │
│   (작동증명 / 상업증거 / cost·impact 단위 / payback / 특허)  │
│   ※ 스코어링 전 필수. 안 하면 4명이 다른 잣대로 채점한다     │
└─────────────────────────────────────────────────────────────┘
      │
      ▼  동일한 EvidencePack + 동일한 임계치를 4명에게 주입
┌──────────────┬──────────────┬──────────────┬───────────────┐
│  a 조원 A    │  b 조원 B    │  c 나        │  d 조원 D     │
│ Structural   │ Economic     │ Physical     │ Proven        │
│ Demand (30)  │ Value (25)   │ Impact (20)  │ Scalability(25)│
└──────────────┴──────────────┴──────────────┴───────────────┘
      │  각자 level(이산 판정) + 근거 인용만 반환. 점수는 안 매긴다.
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2 · 결정론적 채점 & Cut-off       lib/scoring.ts        │
│   ① level → 점수 (Score Pad)                                │
│   ② 필수조건: Proven (A)≥1·(B)≥2 미충족 → 그 원칙 0점       │
│   ③ 하드게이트: Primary Impact Unit 미정의 → 총점 무관 탈락 │
│   ④ 편중방지 Floor: 원칙별 60% 미만 → IC 특별승인 대상      │
│   ⑤ 판정구간: 60~69 Watchlist / 70~84 IC / 85+ fast-track   │
│   ★ LLM이 여기 들어오지 않는다 → 같은 근거면 항상 같은 점수 │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3 · 보고서 작성            lib/agents/report-writer.ts │
│   확정 점수를 **재계산 없이** 받아 IC용 문서로 서술         │
│   판단요약 / 임계치 / Score Pad / 원칙별 의견 / Bear case / │
│   Kill questions / 실사 체크리스트 / 근거와 한계            │
└─────────────────────────────────────────────────────────────┘
      │
      ▼  NDJSON 스트리밍 → 화면에 단계별 실시간 표시
```

### 이 구조를 고른 이유 3가지

1. **근거를 한 번만 모아 4명이 공유한다.**
   4개 에이전트가 각자 크롤링하면 서로 다른 사실 위에서 점수를 매기게 되어 합산이 의미를 잃는다.
   같은 근거 풀에서 판정해야 "왜 a는 높은데 b는 낮은가"를 IC에서 설명할 수 있다. 비용·시간도 1/4.

2. **임계치를 스코어링 전에 확정한다 (STEP 0).**
   철학 문서의 "STEP 0 — 스코어링 전 필수 수행"이 이것이다. SW 기업에 "실환경 가동 1,000시간"을
   들이대면 아무도 통과 못 하고, 원천기술에 "유료 고객 5곳"을 요구하면 전부 탈락한다.

3. **점수는 코드가 매긴다. LLM은 판정만 한다.**
   에이전트는 `level`(예: driver 2개 확인, 해자 3개 충족)만 내고, `level → 점수` 변환과
   게이트 적용은 `lib/scoring.ts`가 한다. 같은 findings면 항상 같은 점수가 나온다.
   LLM에게 "몇 점 줄래?"라고 물으면 매번 달라져서 IC에서 방어가 안 된다.

---

## 조원별 작업 분담

**계약서는 `lib/contract.ts` 하나뿐이다.** 이것만 지키면 서로 코드를 안 봐도 병렬로 개발된다.

```ts
type PrincipleAgent = (input: AgentInput) => Promise<PrincipleFindings>
//                     ↑ 회사 + 확정 임계치 + 공유 근거    ↑ level 판정 + 인용 + red flag
```

| 담당 | 원칙 | 배점 | 건드릴 파일 |
|---|---|---|---|
| 조원 A | a. Structural Demand | 30 | `lib/agents/a-structural-demand.ts` |
| 조원 B | b. Economic Value | 25 | `lib/agents/b-economic-value.ts` |
| **나** | c. Physical Impact | 20 | `lib/agents/c-physical-impact.ts` |
| 조원 D | d. Proven Scalability | 25 | `lib/agents/d-proven-scalability.ts` |
| **나** | 오케스트레이션 | — | `lib/agents/orchestrator.ts`, `calibrate.ts`, `scoring.ts`, `lib/evidence/*` |

각 원칙 파일에서 실제로 손댈 곳은 `EXTRA_GUIDANCE` 문자열 하나다.
모델 호출·스키마 강제·재시도·프롬프트 뼈대는 `lib/agents/runtime.ts`가 이미 처리한다.

더 깊게 만들고 싶으면 c처럼 **여러 단계로 쪼개면 된다** —
`c-physical-impact.ts`는 하드 게이트 때문에 2단계(단위 추출 → 스코어링)로 돌린다.
한 번에 물으면 모델이 "탄소를 줄입니다" 같은 서사를 물리 단위로 착각해 게이트를 통과시켜 버려서,
게이트 판정만 독립 호출로 분리했다.

### 조원 4명이 공유해야 하는 규칙

에이전트가 아무리 잘 써도 이 3개가 깨지면 점수가 의미 없어진다. `runtime.ts`의 `BASE_RULES`에 박아뒀다.

1. **점수를 매기지 않는다.** `level`만 낸다.
2. **모든 판정에 원문 인용을 붙인다.** `evidence[].sourceId`가 EvidencePack에 없으면
   `lib/scoring.ts`가 자동으로 버린다(환각 인용 방어). 인용이 없으면 근거 없는 점수가 된다.
3. **모르면 `unknown`.** 사전지식으로 사실을 만들어내면 실격. `missingData`에 무엇이 없었는지 적는다.

---

## 파일 지도

```
lib/
  philosophy.ts          철학 원문 + Score Pad 루브릭 (단일 진실 원천)
  archetypes.ts          STEP 0 아키타입 6종 표
  contract.ts          ★ 조원 4명 사이의 계약서 (Zod 스키마)
  scoring.ts             결정론적 채점 + Cut-off 엔진 (LLM 없음)
  evidence/
    pack.ts              공유 근거 풀 구성 + 프롬프트 직렬화
    dart.ts              DART OpenAPI (감사보고서 주석 → 수주잔고·계약부채)
    web.ts               웹 검색 (Tavily, 선택)
    zip.ts               무의존 ZIP 해제 (DART가 zip으로 준다)
  agents/
    runtime.ts           원칙 에이전트 공용 런타임 + 절대 규칙
    calibrate.ts         STEP 0
    a~d-*.ts             원칙 에이전트 4개
    report-writer.ts     보고서 작성
    orchestrator.ts    ★ 파이프라인 전체
app/
  page.tsx               입력 → 진행상황 → 스코어카드 → 보고서 스트리밍 UI
  api/report/route.ts    NDJSON 스트리밍 엔드포인트
scripts/
  scoring.test.ts        Cut-off 규칙 10개 테스트
```

---

## 시연 시 주의

- `DART_API_KEY`·`TAVILY_API_KEY`가 없으면 근거가 거의 안 모여서 대부분 `unknown`으로 떨어지고
  점수가 낮게 나온다. **이건 버그가 아니라 설계 의도다** — 근거 없이 점수를 주지 않는다.
  발표 전에 두 키를 발급받거나, "참고 자료 붙여넣기"에 IR 자료를 넣고 돌리면 된다.
- 첫 DART 호출은 전체 기업 고유번호(약 20MB XML)를 받아 캐싱하므로 10~20초 걸린다. 두 번째부터 빠르다.
```
