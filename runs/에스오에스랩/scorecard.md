# 에스오에스랩 · Score Pad

## STEP 0 — 확정 임계치

- 아키타입: **SW · AI · 로보틱스** × 산업 장비 · Hardware
- 분류 근거: 라이다 센서 하드웨어지만 매출이 로보틱스 고객 대상 공급계약 중심이라 SW·로보틱스 앵커를 주로 적용한다.
- 작동 증명: 서로 다른 환경 배포 ≥2 + 성능 재현
- 상업 증거: binding PO ≥2건 또는 반복 구매 고객 ≥1
- cost 단위: $/unit / impact 단위: 사고-저감 건수/설비-yr
- payback 임계: 3년 / 등록특허 하한: 4건

## 점수

| 원칙 | 카테고리 | 점수 | 세부 |
|---|---|---|---|
| a. Structural Demand | 시장성 | **20 / 30** | 구조적 driver 개수 13/16 · Subsidy 의존도 ≤30% (Stress Test 통과) 4/8 · 10년+ 산업변화 설득력 + bottom-up TAM 3/6 |
| b. Economic Value | 시장성 | **15 / 25** | 상업 증거 티어 13/13 · 고객 ROI · Payback 임계 충족 0/8 · Willingness to pay (유상PoC비·repeat·계약부채↑) 2/4 |
| c. Physical Impact | 임팩트성 | **16 / 20** | Primary Impact Unit 정의 (하드 게이트) 4/8 · 4개 기준 중 충족 개수 (2개↑ 만점) 7/7 · 임팩트–매출 연동 (Revenue↑ = Impact↑) 5/5 |
| d. Proven Scalability | 기술성 | **0 / 25** | (A) 기술 작동 증명 (1개↑ 필수) 0/12 · (B) 해자 Defensibility (2개↑ 필수) 2/8 · (C) Scale-up 준비 0/5 |
| **합계** |  | **51 / 100** | Reject |

## 게이트 판정

- 최종: **51/100** — Reject
- Pass: NO
- 하드 게이트: 통과
- 【필수 조건】 Proven Scalability: 필수 조건 미충족 → 0점 처리: (A) 작동 증명 0건 — 1건 이상 필요, (B) 해자 1건 — 2건 이상 필요
- 【편중 방지 Floor】 Proven Scalability 0/25점으로 floor(15점) 미달 → 총점이 70을 넘어도 IC 특별승인 대상입니다.

## 원칙별 상세

### a. Structural Demand — 20/30


Confirmed driver 2개.

- **구조적 driver 개수** 13/16 (level 2, met)
  - Confirmed 2건.
  - 인용 `[web-a-1]` "현대차 로보틱스랩 200억 공급"
- **Subsidy 의존도 ≤30% (Stress Test 통과)** 4/8 (level 1, partial)
  - Unclear.
  - 인용 없음
- **10년+ 산업변화 설득력 + bottom-up TAM** 3/6 (level 1, partial)
  - bottom-up 미분해.
  - 인용 없음


**미확인 데이터**
- 정부과제 비중

**Kill questions**
- 현대차 외 고객은?

<details><summary>담당 스킬 상세 리포트</summary>

## Structural Demand Verdict
Verdict: CONDITIONAL PASS
(표 생략)

</details>

### b. Economic Value — 15/25


공급계약 확인.

- **상업 증거 티어** 13/13 (level 4, met)
  - 단일판매·공급계약 공시.
  - 인용 `[dart-index]` "20260616 단일판매ㆍ공급계약체결"
- **고객 ROI · Payback 임계 충족** 0/8 (level 0, unknown)
  - payback 미공개.
  - 인용 없음
- **Willingness to pay (유상PoC비·repeat·계약부채↑)** 2/4 (level 1, partial)
  - 일부 확인.
  - 인용 없음

**Red flags**
- 고객 집중도

**미확인 데이터**
- 고객 ROI


<details><summary>담당 스킬 상세 리포트</summary>

## Economic Value Verdict
Verdict: PASS
(표 생략)

</details>

### c. Physical Impact — 16/20


단위는 있으나 경계 모호.

- **Primary Impact Unit 정의 (하드 게이트)** 4/8 (level 1, partial)
  - 단위는 지목되나 경계 모호.
  - 인용 없음
- **4개 기준 중 충족 개수 (2개↑ 만점)** 7/7 (level 2, met)
  - 2개 충족.
  - 인용 없음
- **임팩트–매출 연동 (Revenue↑ = Impact↑)** 5/5 (level 2, met)
  - 직결.
  - 인용 없음

**Red flags**
- baseline 비교 부재

**미확인 데이터**
- 산정식


<details><summary>담당 스킬 상세 리포트</summary>

## Physical Impact Verdict
Verdict: CONDITIONAL PASS
(표 생략)

</details>

### d. Proven Scalability — 0/25

> ⛔ 필수 조건 미충족 → 0점 처리: (A) 작동 증명 0건 — 1건 이상 필요, (B) 해자 1건 — 2건 이상 필요

조원 D 파이썬 에이전트 판정: INSUFFICIENT_EVIDENCE, 자체 점수 0/25 (A 0/12 · B 0/8 · C 0/5). 근거 커버리지 40%.

- **(A) 기술 작동 증명 (1개↑ 필수)** 0/12 (level 0, unmet)
  - 조원 D의 결정론 채점기 판정: A1_poc_reproducibility=UNVERIFIABLE, A2_third_party_validation=NOT_MET, A3_field_operation_hours=UNVERIFIABLE. MET 0건. 아키타입 sw_ai_robotics 기준으로 임계치를 적용했다. 주의: 알 수 없는 아키타입 'sw_ai_robotics' — 원칙 원문의 중립 기준을 적용했다.
  - 인용 `[psa-1]` "연혁에 '2024.01 시험검증용 파일럿 시설 구축', '2026.03 시험검증용 파일럿 시설 확장 이전'이 있으나, materials 기준이 요구하는 Pilot run 2회 이상·고객 qualification 1건 이상·재현성 ±10~20% 수치가 어디에도 제시되지 않는다. 시설의 존재와 파일럿 실행 실적은 다르다."
  - 인용 `[psa-2]` "연혁의 인증은 '2020.06 벤처인증(기술보증기금)', '2020.10 중소기업 확인(중소벤처기업부)'뿐이다. 둘 다 기업 지위에 대한 행정 인증이고, 원칙이 요구하는 제3자 공인시험기관의 시험성적서나 제품·기술 인증이 아니다."
  - 인용 `[psa-3]` "materials 기준은 배치 수와 수율 재현성으로 본다. 파일럿 시설 구축·확장 사실은 확인되나 누적 배치 수, 수율, 재현 폭 수치를 찾지 못했다."
- **(B) 해자 Defensibility (2개↑ 필수)** 2/8 (level 1, met)
  - 조원 D의 결정론 채점기 판정: B1_exchange_tech_grade=UNVERIFIABLE, B2_registered_patents=UNVERIFIABLE, B3_domain_expertise=UNVERIFIABLE, B4_lab_publication_track=MET. MET 1건 (2건 이상이어야 필수 조건 충족).
  - 인용 `[psa-4]` "거래소 기술성 평가 등급을 확인할 자료를 찾지 못했다. 상장 준비 단계나 기술특례 트랙 여부가 공개되어 있지 않다."
  - 인용 `[psa-5]` "'세계 최초로 그래핀에 나노홀을 일괄 형성하는 양산 기술, 금속에서 그래핀을 기르는 기술 등 독창적인 연구개발 노하우를 갖추고 있다'는 기술 보유 서술은 있으나, 등록 특허 건수와 청구항 구조는 제시되지 않는다. DART에도 이 회사의 공시가 없어 확인 경로가 없다."
  - 인용 `[psa-6]` "'2021.03 기업부설연구소 설립(과학기술정보통신부)'이 확인되나, 연구 인력의 규모와 학위별 구성(석사 이상 비중)은 공개되어 있지 않다."
- **(C) Scale-up 준비** 0/5 (level 0, unmet)
  - 조원 D의 결정론 채점기 판정: C1_capacity_plan=NOT_MET, C2_capex_funding=NOT_MET, C3_supply_chain=UNVERIFIABLE. MET 0건.
  - 인용 `[psa-8]` "'2022.06 Fabrication Zero 완공(서울대연구공원)', '2024.01 시험검증용 파일럿 시설 구축', '2026.03 시험검증용 파일럿 시설 확장 이전'. 시점은 명시되나 증설 규모(생산능력·면적)가 제시되지 않고, 시험검증용 파일럿이지 양산 라인 증설 로드맵이 아니다."
  - 인용 `[psa-9]` "2020년 개인엔젤부터 2025년 인비저닝파트너스·에이티넘인베스트먼트·IBK기업은행까지 5회 이상 투자유치가 확인되고, 2022.06에는 유안타인베스트먼트·KB증권·에이티넘인베스트먼트·KDB산업은행·JB인베스트먼트가 참여했다. 다만 조달 금액이 공개되지 않았고, 조달 자금이 증설에 쓰인다는 용도 연결이 어디에도 없다."
  - 인용 `[psa-10]` "핵심 원료·부품의 공급 계약이나 이중 소싱 확보를 확인할 자료를 찾지 못했다. 그래핀 전구체·기재 금속의 조달 구조에 대한 언급이 공개 자료에 없다."

**Red flags**
- [조사 결함] 에스오에스랩 20260515002099: '계약부채' 등 Economic Value 축(원칙 b) 신호가 감사보고서 주석에 있다 — 이 축(기술성)의 Evidence로는 만들지 않는다. 해당 축을 담당하는 에이전트에게 전달할 것.
- [조사 결함] 에스오에스랩 20260515002099: 'B3_domain_expertise' 관련 섹션은 찾았지만 표를 명확히 읽지 못했다 — 추측하지 않고 건너뛴다 (UNVERIFIABLE로 남는다).
- [조사 결함] 에스오에스랩 20251118000163: 'B3_domain_expertise' 관련 섹션은 찾았지만 표를 명확히 읽지 못했다 — 추측하지 않고 건너뛴다 (UNVERIFIABLE로 남는다).
- [조사 결함] 에스오에스랩 20251114002154: 'B3_domain_expertise' 관련 섹션은 찾았지만 표를 명확히 읽지 못했다 — 추측하지 않고 건너뛴다 (UNVERIFIABLE로 남는다).
- [조사 결함] 에스오에스랩 20250814002878: 'B3_domain_expertise' 관련 섹션은 찾았지만 표를 명확히 읽지 못했다 — 추측하지 않고 건너뛴다 (UNVERIFIABLE로 남는다).
- [조사 결함] MET 1건이 3~4급(언론·회사 자체 발표) 근거에만 의존한다: B4_lab_publication_track. 1~2급 근거로 보강되기 전까지는 실사에서 재확인할 것.
- D 자체 게이트 미충족 블록: A, B

**미확인 데이터**
- A1_poc_reproducibility — 근거를 확인하지 못했다
- A3_field_operation_hours — 근거를 확인하지 못했다
- B1_exchange_tech_grade — 근거를 확인하지 못했다
- B2_registered_patents — 근거를 확인하지 못했다
- B3_domain_expertise — 근거를 확인하지 못했다
- C3_supply_chain — 근거를 확인하지 못했다

**Kill questions**
- [A1_poc_reproducibility] PoC 재현성 — 공개 자료에서 확인할 수 없었다. 판정 기준: 서로 다른 고객·환경에서 PoC 2회 이상, 핵심 성능 KPI가 ±10~20% 내 재현
- [A3_field_operation_hours] 실환경 가동 — 공개 자료에서 확인할 수 없었다. 판정 기준: 실환경 누적 가동 1,000시간 이상
- [B1_exchange_tech_grade] 거래소 기술성 평가 — 공개 자료에서 확인할 수 없었다. 판정 기준: 거래소 기술성 평가 A 이상 (기술특례상장 기준 등급)
- [B2_registered_patents] 등록 특허 — 공개 자료에서 확인할 수 없었다. 판정 기준: 등록 특허 3건 이상 (출원 아님). 핵심 청구항의 경쟁사 회피 난이도를 함께 본다
- [B3_domain_expertise] 도메인 전문성 — 공개 자료에서 확인할 수 없었다. 판정 기준: 관련 도메인 석사 이상 인력 비중 60% 이상
- [C3_supply_chain] 공급망 확보 — 공개 자료에서 확인할 수 없었다. 판정 기준: 핵심 원료·부품의 공급 계약 또는 이중 소싱이 확보되어 있다


## 근거 수집 공백

- 웹 검색 결과 1건은 기업명이 언급되지 않아 관련성 필터에서 제외했습니다.

