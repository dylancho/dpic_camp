# Proven Scalability 에이전트 설계

작성 2026-08-12 · 드림인베스터클럽 캠프 5조 · 브랜치 `Proven-Scalability-agent`

## 1. 무엇을 만드는가

pre-IPO 기업 투자 검토 멀티 에이전트 시스템에서 **하우스 투자 원칙 (d) Proven Scalability
(기술성, 25점)** 을 담당하는 하위 에이전트.

"실험이 아니라, 실제로 구현되며 해당 팀만이 가진 해자여야 한다"를 세 블록으로 판정한다.

| 블록 | 내용 | 게이트 | 배점 |
|---|---|---|---|
| (A) 기술 작동 증명 | PoC 재현성 · 제3자 인증 · 실환경 누적 가동 | 1개 이상 필수 | 12 |
| (B) 해자 | 기술성 평가 등급 · 등록 특허 · 인력 전문성 · 랩·논문 이력 | 2개 이상 필수 | 8 |
| (C) Scale-up 준비 | 양산 경로 3요소 | 없음 | 5 |

## 2. 설계의 중심 결정

### 2.1 수집(LLM)과 판정(코드)을 분리한다

하우스 원칙 (d)는 이미 셀 수 있는 규칙으로 쓰여 있다 — `PoC ≥ 2회`, `인증 ≥ 2`,
`가동 ≥ 1,000시간`, `석사 이상 ≥ 60%`, `특허 ≥ 3~5건`. 이 카운팅을 LLM에 맡기면
같은 기업을 두 번 돌렸을 때 판정이 갈린다. 투자 심사에서 재현되지 않는 판정은 쓸 수 없다.

따라서:

- **리서처(LLM)** 는 증거만 수집한다. 점수도 게이트 통과 여부도 계산하지 않는다.
- **`scoring.py`(순수 Python)** 가 카운팅·등급 필터·게이트 판정·배점을 전부 수행한다.

`scoring.py`에는 LLM 호출이 없다. 같은 증거 집합이면 항상 같은 점수가 나오고,
LLM 없이 단위 테스트할 수 있으며, 하우스 기준이 바뀌면 `criteria.py`만 고치면 된다.

### 2.2 "근거 없음"과 "기준 미달"을 구분한다

pre-IPO 비상장은 DART 공시 의무가 없는 곳이 많고, 제3자 시험성적서나 실환경 누적
가동시간은 공개 소스에 거의 나오지 않는다. 이 둘을 뭉치면 확인 불가가 전부 미충족으로
흘러가 대부분의 기업이 기계적으로 탈락하고, 에이전트의 변별력이 사라진다.

각 항목은 세 상태를 갖는다.

| 상태 | 의미 |
|---|---|
| `MET` | 근거를 찾았고 임계치를 충족 |
| `NOT_MET` | 근거를 찾았으나 임계치 미달 |
| `UNVERIFIABLE` | 판정할 근거를 찾지 못함 |

`UNVERIFIABLE`은 점수에 0으로 기여하지만 `NOT_MET`과 다르게 취급된다. 게이트를 넘지
못한 원인이 `UNVERIFIABLE`이면 verdict은 `FAIL`이 아니라 `INSUFFICIENT_EVIDENCE`이며,
해당 항목들은 실사 질문 리스트로 출력된다.

### 2.3 증거의 출처를 등급으로 강제한다

원칙에 "Founder 자체 테스트만 있으면 불인정"이 명시돼 있다. 이를 프롬프트 훈계가 아니라
코드 규칙으로 강제한다.

| 등급 | 출처 |
|---|---|
| 1 | DART 공시 · 감사보고서 주석 · 등록 특허 원문 · 거래소 기술성 평가 |
| 2 | 제3자 공인 시험성적서 · 독립 인증기관 · peer-reviewed 논문 |
| 3 | 언론 보도 · 산업 리포트 |
| 4 | 회사 자체 발표 · IR 자료 · 홈페이지 |

**등급 필터**: 어떤 항목이 3~4급 근거만으로 뒷받침되면 `MET`으로 승격하지 않고
`UNVERIFIABLE`로 강등한다. 언론 보도만 있는 PoC 2건은 충족이 아니라 실사 확인 대상이다.

### 2.4 아키타입 임계치는 PM 에이전트에서 주입받는다

STEP 0 Threshold Calibration은 PM 에이전트가 기업당 한 번 수행한다. 본 에이전트는
분류를 직접 하지 않고, 주입된 아키타입과 임계치를 그대로 적용한다.

4개 축 에이전트가 각자 분류하면 같은 기업이 축마다 다른 아키타입으로 평가되어 최종
100점이 내부적으로 모순된다. 특히 EN2CORE(플라즈마 장비를 파는 원천기술),
Neubility(하드웨어를 만드는 SW)처럼 혼합 아키타입에서 갈린다.

임계치가 주입되지 않은 경우 **자체 추정하지 않는다.** 아키타입 중립 기준으로 실행하되
결과에 `calibration: uncalibrated` 를 명시한다. 조용히 추측하면 PM 판단과 어긋난 채로
점수만 상위에 올라간다.

## 3. 배점

### (A) 기술 작동 증명 — 12점, 게이트 1개 이상

| 항목 ID | 기준 |
|---|---|
| `A1_poc_reproducibility` | 서로 다른 고객·환경 PoC ≥ 2회, 핵심 KPI ±10~20% 내 재현 |
| `A2_third_party_validation` | 제3자 시험성적서 · 독립 인증 ≥ 2 |
| `A3_field_operation_hours` | 실환경 누적 가동 ≥ 1,000시간 (또는 산업별 준하는 장기 validation) |

충족 개수 1 / 2 / 3 → **8 / 10 / 12점**

`A3`의 1,000시간은 아키타입별로 치환된다. 원천기술은 하드웨어 기준을 그대로 적용하지
않고 pilot plant 가동 + TRL 6+ 로, SW·AI는 서로 다른 환경 배포 ≥ 2 + 성능 재현으로 본다.

### (B) 해자 — 8점, 게이트 2개 이상

| 항목 ID | 기준 |
|---|---|
| `B1_exchange_tech_grade` | 거래소 기술성 평가 A 이상 |
| `B2_registered_patents` | 등록 특허 (출원 아님). 건수 하한은 아키타입별. 핵심 청구항의 회피 난이도 |
| `B3_domain_expertise` | 관련 도메인 석사 이상 인력 비중 ≥ 60% |
| `B4_lab_publication_track` | 핵심 인력의 관련 랩 근무 이력 · peer-reviewed 논문 · 핵심 특허 보유 |

충족 개수 2 / 3 / 4 → **5 / 7 / 8점**

### (C) Scale-up 준비 — 5점, 게이트 없음

양산 경로 3요소. 하우스 원칙 원문에 세부 기준이 없어 본 설계에서 정의했다 (§7 참조).

| 항목 ID | 기준 (하드웨어·소재·에너지) | SW·AI·로보틱스 치환 |
|---|---|---|
| `C1_capacity_plan` | 생산능력 확대 계획 (라인·플랜트 증설 로드맵) | 인프라 확장 계획 |
| `C2_capex_funding` | capex 조달 계획 (자금 출처가 특정됨) | 조직·인력 확장 계획 |
| `C3_supply_chain` | 원료·부품 공급망 확보 (계약 또는 이중 소싱) | 재현 가능한 배포 파이프라인 |

충족 개수 1 / 2 / 3 → **2 / 4 / 5점**

### 게이트 미충족 처리

A가 0개거나 B가 1개 이하면 해당 블록을 0점 처리하고 `gate_failed` 플래그를 상위로 올린다.
**전체 탈락 여부는 본 에이전트가 정하지 않는다.** 25점 한 축이 하우스 100점 판정을
독단할 수 없으므로 PM 에이전트가 판단한다.

## 4. 출력 계약

```
ProvenScalabilityResult
  verdict            PASS | FAIL | INSUFFICIENT_EVIDENCE
  score              0~25
  block_scores       {A: 0~12, B: 0~8, C: 0~5}
  gate_failed        [] | ["A"] | ["B"] | ["A","B"]
  evidence_coverage  0.0~1.0   조사 항목 중 UNVERIFIABLE이 아닌 비율
  calibration        아키타입 · 적용 임계치 · 주입 여부
  evidence           Evidence[]
  diligence_questions  string[]   UNVERIFIABLE 항목에서 생성
```

```
Evidence
  criterion_id     A1_poc_reproducibility 등
  status           MET | NOT_MET | UNVERIFIABLE
  source_tier      1~4
  source_url
  quote            판단 근거가 된 원문 인용
  extracted_value  PoC 건수 · 가동시간 · 특허 건수 · 석사 비중 등 정량값
```

`verdict` 3값을 상위 오케스트레이터가 받아줄 수 있는지는 팀 확인 필요 (§7).

### verdict 결정 규칙

`scoring.py`가 아래 순서로 판정한다. 커버리지 수치는 verdict를 바꾸지 않는다 —
verdict는 오직 게이트 미충족의 **원인**으로 결정된다.

1. A·B 게이트를 모두 통과 → `PASS`
2. 게이트를 못 넘겼고, 그 게이트에 `UNVERIFIABLE` 항목이 하나라도 있어 **추가 근거가
   나오면 통과할 가능성이 남아 있음** → `INSUFFICIENT_EVIDENCE`
3. 게이트를 못 넘겼고, 그 게이트의 모든 항목이 `NOT_MET` (근거를 찾았고 미달) → `FAIL`

`FAIL`은 조사가 끝났다는 뜻이고, `INSUFFICIENT_EVIDENCE`는 실사로 넘긴다는 뜻이다.

**증거 커버리지를 항상 함께 반환하는 이유**: 점수만 올리면 "근거를 못 찾았다"가
"기준에 못 미친다"로 세탁된다. 커버리지가 낮은 25점 만점과 높은 25점 만점은 전혀 다른
정보다.

## 5. 구조

```
agents/proven_scalability/
  schema.py       Evidence · GateResult · ProvenScalabilityResult
  criteria.py     A/B/C 항목 정의 + 아키타입별 임계치 치환 규칙
  scoring.py      순수 함수. Evidence[] → 점수·게이트·verdict. LLM 없음
  researcher.py   Claude Agent SDK 서브에이전트: tech_proof / moat / scaleup
  tools/
    dart.py       DART OpenAPI. 공시·감사보고서 주석
    kipris.py     인터페이스만. 키 미확보 (§6)
    web.py        웹 검색 — 인증·논문·언론
  prompts/
    tech_proof.md · moat.md · scaleup.md
tests/
  test_scoring.py    배점·게이트·등급필터 결정론 검증
  test_criteria.py   아키타입별 임계치 치환
  fixtures/          고정 Evidence 세트
```

스택: Python + Claude Agent SDK. 리서처 3개는 각자 자기 블록 항목만 조사한다.
블록을 나누는 이유는 프롬프트 비대화를 막고 A/B 판정이 서로 오염되지 않게 하기 위함이다.

## 6. 데이터 소스와 한계

| 소스 | 상태 | 용도 |
|---|---|---|
| DART OpenAPI | 키 확보됨 | 감사보고서 주석(수주잔고·계약부채·무형자산·산업재산권), 기술성 평가 관련 서류 |
| 웹 검색 | 가능 | 제3자 인증, peer-reviewed 논문, 언론 보도 |
| KIPRIS | **키 미확보** | 등록 특허 건수·청구항 구조 |

**KIPRIS 부재의 결과**: `B2_registered_patents`는 DART 무형자산·산업재산권 주석과 웹
검색으로 대체한다. 이 경로로는 등록 건수의 근사치까지는 가능하나 "핵심 청구항이 경쟁사
회피가 어려운 구조인가"는 판정할 수 없다. 따라서 `B2`는 상당수 `UNVERIFIABLE`로 떨어져
실사 질문으로 넘어간다. `tools/kipris.py`는 인터페이스만 정의해 두고, 키 확보 시
그 자리에 구현을 넣는다.

DART 키는 `.env`에서 읽는다. 키 값은 커밋하지 않는다.

## 7. 미해결 — 팀 확인 필요

1. **(C) Scale-up 5점의 기준이 하우스 원칙 원문에 없다.** 스코어표에는 5점으로 배정돼
   있으나 (A)·(B)와 달리 정의가 이름뿐이다. §3의 3요소는 본 설계의 제안이며 팀 승인이 필요하다.
2. **`INSUFFICIENT_EVIDENCE`를 상위 오케스트레이터가 받아줄 수 있는가.** PASS/FAIL
   이분법만 받는 구조라면 계약을 다시 맞춰야 한다.
3. **아키타입별 특허 건수 하한** (`B2`) 이 미정이다. 원칙에 "소재·장비 ≥ 3~5건" 예시만 있다.
4. **PM 에이전트의 임계치 주입 포맷**이 미정이다. 확정 전까지 `criteria.py`가 기대하는
   구조를 본 설계 기준으로 두고, PM 스펙이 나오면 어댑터를 넣는다.

## 8. 범위

이 브랜치의 PR은 `agents/proven_scalability/` 와 그 테스트만 포함한다.
공통 오케스트레이터·다른 축 에이전트·STEP 0 분류 모듈은 건드리지 않는다.
