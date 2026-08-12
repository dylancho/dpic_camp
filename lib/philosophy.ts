/**
 * 양양 5조 하우스 투자철학 — 단일 진실 원천(Single Source of Truth).
 *
 * 이 파일은 4명의 조원이 각자 만드는 원칙 에이전트가 **공유하는 헌법**이다.
 * 프롬프트에 들어가는 철학 원문, 그리고 코드가 결정론적으로 채점하는 루브릭이 함께 있다.
 *
 * 중요한 설계 원칙:
 *   LLM은 "점수"를 매기지 않는다. LLM은 각 기준의 **충족 레벨(level)** 만 판정하고,
 *   레벨 → 점수 변환은 아래 RUBRIC이 코드로 수행한다.
 *   (같은 기업을 두 번 돌려도 점수 산식이 흔들리지 않게 하기 위함)
 */

export const HOUSE_ONE_LINER =
  '우리는 임팩트에 투자하지만, 임팩트라는 이유로 투자하지 않습니다. ' +
  '구조적 수요·검증된 기술·고객 손익·측정 가능한 임팩트가 만나는 지점에만 투자합니다.';

export const HOUSE_PHILOSOPHY = `
[우리 하우스의 투자 철학]
a. Structural, not cyclical.  정책도 유행도 아닌, 구조적 수요에 투자한다.
b. Economic, not ideological. 신념이 아니라 손익으로 증명되어야 한다.
c. Physical, not narrative.   임팩트는 이야기가 아니라, 측정 가능하고 산업 규모로 확장되는 물리량이어야 한다.
d. Scalable, not experimental. 실험이 아니라, 기술 검증을 마치고 대규모 상업화를 앞둔 기업에 투자한다.

[배분 논리] 시장성 55(30+25) · 기술성 25 · 임팩트성 20.
"구조적으로 커질 미래 시장을 먼저 보고 → 실제 손익으로 검증하고 → 증명된 기술로 → 측정 가능한 임팩트를 낸다"
는 순서를 그대로 가중치에 반영했다.
`.trim();

export type PrincipleId =
  | 'structural_demand'
  | 'economic_value'
  | 'physical_impact'
  | 'proven_scalability';

export const PRINCIPLE_ORDER: PrincipleId[] = [
  'structural_demand',
  'economic_value',
  'physical_impact',
  'proven_scalability',
];

export const PRINCIPLE_META: Record<
  PrincipleId,
  { key: 'a' | 'b' | 'c' | 'd'; name: string; category: string; owner: string }
> = {
  structural_demand: { key: 'a', name: 'Structural Demand', category: '시장성', owner: '조원 A' },
  economic_value: { key: 'b', name: 'Economic Value', category: '시장성', owner: '조원 B' },
  physical_impact: { key: 'c', name: 'Physical Impact', category: '임팩트성', owner: '나 (오케스트레이터 겸임)' },
  proven_scalability: { key: 'd', name: 'Proven Scalability', category: '기술성', owner: '조원 D' },
};

/* ------------------------------------------------------------------ *
 * 원칙별 상세 정의 — 각 원칙 에이전트의 시스템 프롬프트에 그대로 주입된다
 * ------------------------------------------------------------------ */

export const PRINCIPLE_DEFINITION: Record<PrincipleId, string> = {
  structural_demand: `
【a. Structural Demand (시장성) — 30점】
"기업의 경제적 의사결정을 바꾸는 비가역적, 장기적 산업 변화에서 나오는 수요가 존재하여야 한다."
— 아래 5개 driver 중 최소 2개 이상 존재하여야 원칙을 충족한다.

1. Resource Constraint — 전력·핵심광물·물·노동력 등 물리적 자원 부족이 구매를 유발하는 문제인가.
   (ex. 전력부족→ESS, 광물불안→recycling, 인력부족→robotics)
2. Cost Curve Shift — unsubsidized 기준 $/kWh, $/kg, $/ton의 지속적 개선 경로가 존재하는 문제인가.
3. Infrastructure Replacement Cycle — grid modernization, factory automation, 데이터센터 전력 등
   장기 capex cycle에 걸린 문제인가.
4. Supply Chain Reconfiguration — 비용 외 공급안정성·지정학·lead time 때문에 공급망을 재편하는
   문제를 다루는가. (critical minerals, battery/semiconductor materials)
5. Productivity Imperative — 인력·에너지·원료 문제로 신기술 도입이 불가피한 상황을 푸는 문제인가.

★ 보조금(subsidy) 의존도 Stress Test: 보조금·정책 인센티브를 0으로 두었을 때도 수요가 남는가.
  매출/경제성의 보조금 기여분이 30% 이하여야 통과. "정책이 만든 수요"는 cyclical로 간주한다.
★ TAM은 top-down 시장보고서 인용이 아니라, (도입 대상 설비 수 × 단가 × 침투율) 형태의
  bottom-up 논리로 서술 가능해야 한다.
`.trim(),

  economic_value: `
【b. Economic Value (시장성) — 25점】
"임팩트 이전에 고객의 P&L을 개선하여야 한다." — 아래 중 1개 이상 존재해야 한다.

1. 서로 다른 고객과 실제 산업환경에서 진행한 **유상** PoC ≥ 2건
2. 반복 구매하는 Commercial Customer ≥ 1
3. Binding contract / PO / off-take ≥ 2건
4. 위 데이터를 구할 수 없는 경우, DART 감사보고서 **주석**에 명시된
   수주잔고 / 계약부채 / 건설형공사계약 항목의 **추이**로 판단

★ MOU · LOI · 업무협약 · 전략적 파트너십 보도자료는 **0점**이다. 돈이 오간 증거만 인정한다.
★ 고객 ROI/Payback: 고객이 이 제품을 샀을 때 몇 년 만에 회수되는가. 아키타입별 임계치를 따른다.
★ Willingness to pay: 유상 PoC 비중, 반복 구매, 계약부채 증가 추이로 판단한다.
`.trim(),

  physical_impact: `
【c. Physical Impact (임팩트성) — 20점】
"단순 스토리텔링이 아니라, 실제로 사회 문제를 해결하는 방법이여야 한다."
— 아래 4개 기준 중 2개 이상이 존재해야 한다.

1. 저감 메커니즘의 진술 가능성 — 공정의 **어떤 배출**이 줄어드는지가 설명된다.
2. 대체 대상의 특정 — 도입 고객의 공정에서 대체되는 **기존 설비 또는 원료가 이름으로 지목**된다.
3. 저감 규모가 파악 가능하다 — 총 배출량 대비 비율 혹은 명확한 물리량 단위로 표현된다.
4. baseline 대비 정량 비교 — 동일 기능을 하는 기존 방식보다 단위당 저감 효율이 높거나 비용이
   낮다는 점이 정량 비교로 제시된다. (기존 대안보다 못하면 물리적 임팩트가 있어도 채택되지
   않으므로 반드시 baseline 대비 비교를 바탕으로 한다)

★★ 하드 게이트: **Primary Impact Unit** (tCO2e/unit, kg-회수/ton, m³-절수/yr, kWh-절감/yr 등
   측정 가능한 단일 물리 단위)가 정의되지 않으면 총점과 무관하게 **탈락**한다.
   측정 불가능한 임팩트는 서사(narrative)로 간주한다.
★ 임팩트–매출 연동: 매출이 늘면 임팩트도 같이 느는 구조인가(Revenue↑ = Impact↑).
   임팩트가 매출과 무관한 부수 활동(CSR, 상쇄 크레딧 구매 등)이면 연동으로 인정하지 않는다.
`.trim(),

  proven_scalability: `
【d. Proven Scalability (기술성) — 25점】
"실험이 아니라, 실제로 구현되며 해당 팀만이 가진 해자여야 한다."

(A) 기술 작동 증명 — 다음 중 **1개 이상 필수** (미충족 시 이 원칙 0점)
  a. 서로 다른 고객·환경에서 PoC ≥ 2회, 핵심 성능 KPI가 ±10~20% 내 재현
  b. 제3자 시험성적서 · 독립 인증 ≥ 2 (Founder 자체 테스트만 있으면 불인정)
  c. 하드웨어·산업기술은 실환경 누적 가동 ≥ 1,000시간
     (또는 산업 특성상 이에 준하는 장기 validation)

(B) 해자 Defensibility — 다음 중 **2개 이상 필수** (미충족 시 이 원칙 0점)
  a. 거래소 기술성 평가 A 이상 (기술특례상장 기준 등급)
  b. 등록 특허 보유 — 단순 출원 건수보다, 핵심 청구항이 경쟁사 회피가 어려운 구조인지로 판단
     (건수 하한은 산업별 설정; 예: 소재·장비 ≥ 3~5건)
  c. 핵심 인력의 도메인 전문성 — 관련 도메인 석사 이상 인력 비중 ≥ 60%
  d. 핵심 인력이 관련 도메인 랩실 근무 이력을 갖거나, 해당 기술에 관한 peer-reviewed 논문·
     핵심 특허를 보유한다.

(C) Scale-up 준비 — 양산 라인/파운드리 계약, 원료 조달 확보, 인증 로드맵, CapEx 조달 계획 등
`.trim(),
};

/* ------------------------------------------------------------------ *
 * Score Pad (100점 만점) — 결정론적 채점 루브릭
 * points[level] = 획득 점수. level은 에이전트가 판정한 이산값.
 * ------------------------------------------------------------------ */

export type CriterionSpec = {
  id: string;
  label: string;
  max: number;
  /** level → 점수. 배열 인덱스가 곧 level이다. */
  points: number[];
  /** 에이전트에게 "level을 이렇게 매겨라"라고 알려주는 설명 */
  levelGuide: string;
};

export type PrincipleSpec = {
  id: PrincipleId;
  max: number;
  /** 편중 방지 Floor — 자기 배점의 60% */
  floorRatio: number;
  criteria: CriterionSpec[];
};

export const RUBRIC: Record<PrincipleId, PrincipleSpec> = {
  structural_demand: {
    id: 'structural_demand',
    max: 30,
    floorRatio: 0.6,
    criteria: [
      {
        id: 'sd.drivers',
        label: '구조적 driver 개수',
        max: 16,
        points: [0, 8, 13, 16],
        levelGuide:
          'level = 근거로 확인된 구조적 driver 개수 (5개 중). 3개 이상이면 level 3으로 고정(cap). ' +
          '"이 driver가 고객의 경제적 의사결정을 실제로 바꾸는가"를 통과한 것만 센다.',
      },
      {
        id: 'sd.subsidy',
        label: 'Subsidy 의존도 ≤30% (Stress Test 통과)',
        max: 8,
        points: [0, 4, 8],
        levelGuide:
          'level 0 = 보조금/정책 없으면 수요가 사라진다(의존도 >60% 또는 판단 불가). ' +
          'level 1 = 부분 의존(30~60%), 보조금 축소 시 성장은 둔화하나 수요 자체는 남는다. ' +
          'level 2 = 의존도 ≤30%, unsubsidized 기준으로도 고객이 산다.',
      },
      {
        id: 'sd.tam',
        label: '10년+ 산업변화 설득력 + bottom-up TAM',
        max: 6,
        points: [0, 3, 6],
        levelGuide:
          'level 0 = top-down 시장보고서 인용뿐이거나 근거 없음. ' +
          'level 1 = 장기 변화 서사는 설득력 있으나 TAM이 bottom-up으로 분해되지 않음. ' +
          'level 2 = 10년+ 비가역 변화 + (대상 설비수 × 단가 × 침투율) 형태의 bottom-up TAM 제시 가능.',
      },
    ],
  },

  economic_value: {
    id: 'economic_value',
    max: 25,
    floorRatio: 0.6,
    criteria: [
      {
        id: 'ev.tier',
        label: '상업 증거 티어',
        max: 13,
        points: [0, 3, 6, 10, 13],
        levelGuide:
          'level 0 = 증거 없음 또는 MOU·LOI·업무협약뿐 (MOU/LOI는 반드시 0). ' +
          'level 1 = 무상 PoC / 데모 / 정부 실증과제만. ' +
          'level 2 = 유상 PoC 1건 또는 단발 매출. ' +
          'level 3 = 서로 다른 고객 대상 유상 PoC ≥2건, 또는 반복 구매 Commercial Customer ≥1. ' +
          'level 4 = Binding contract/PO/off-take ≥2건, 또는 DART 주석상 수주잔고·계약부채가 증가 추세.',
      },
      {
        id: 'ev.roi',
        label: '고객 ROI · Payback 임계 충족',
        max: 8,
        points: [0, 4, 8],
        levelGuide:
          'level 0 = 고객 측 경제성이 제시되지 않음(자사 매출만 이야기함). ' +
          'level 1 = 정성적 절감 주장은 있으나 payback 수치가 없음. ' +
          'level 2 = 아키타입 임계치(calibration의 paybackThresholdYears) 이내 payback이 수치로 제시·검증됨.',
      },
      {
        id: 'ev.wtp',
        label: 'Willingness to pay (유상PoC비·repeat·계약부채↑)',
        max: 4,
        points: [0, 2, 4],
        levelGuide:
          'level 0 = 무상 비중이 지배적이거나 판단 불가. ' +
          'level 1 = 유상 전환 사례가 일부 확인. ' +
          'level 2 = 유상 PoC 비중이 높고 반복 구매·계약부채 증가가 함께 확인.',
      },
    ],
  },

  physical_impact: {
    id: 'physical_impact',
    max: 20,
    floorRatio: 0.6,
    criteria: [
      {
        id: 'pi.unit',
        label: 'Primary Impact Unit 정의 (하드 게이트)',
        max: 8,
        points: [0, 4, 8],
        levelGuide:
          'level 0 = 측정 가능한 단일 물리 단위가 정의되지 않음 → 하드 게이트 탈락. ' +
          'level 1 = 단위는 지목되나 산정 경계(무엇 대비, 어느 범위)가 모호함. ' +
          'level 2 = 단위 + 산정 경계 + 산정식이 명확하다 (예: tCO2e/ton-제품, 기존 공정 baseline 대비).',
      },
      {
        id: 'pi.criteria4',
        label: '4개 기준 중 충족 개수 (2개↑ 만점)',
        max: 7,
        points: [0, 3, 7, 7, 7],
        levelGuide:
          'level = 4개 기준(저감 메커니즘 / 대체 대상 특정 / 저감 규모 / baseline 정량비교) 중 충족 개수.',
      },
      {
        id: 'pi.linkage',
        label: '임팩트–매출 연동 (Revenue↑ = Impact↑)',
        max: 5,
        points: [0, 2, 5],
        levelGuide:
          'level 0 = 임팩트가 매출과 무관하거나 부수 활동(CSR·크레딧 구매). ' +
          'level 1 = 연동되나 비선형/부분적. ' +
          'level 2 = 제품 1단위 판매 = 임팩트 N단위로 구조적으로 직결된다.',
      },
    ],
  },

  proven_scalability: {
    id: 'proven_scalability',
    max: 25,
    floorRatio: 0.6,
    criteria: [
      {
        id: 'ps.working',
        label: '(A) 기술 작동 증명 (1개↑ 필수)',
        max: 12,
        points: [0, 8, 10, 12],
        levelGuide: 'level = (A)의 a/b/c 세 항목 중 충족 개수 (0~3). 0이면 이 원칙 전체가 0점 처리된다.',
      },
      {
        id: 'ps.moat',
        label: '(B) 해자 Defensibility (2개↑ 필수)',
        max: 8,
        points: [0, 2, 5, 7, 8],
        levelGuide: 'level = (B)의 a/b/c/d 네 항목 중 충족 개수 (0~4). 2 미만이면 이 원칙 전체가 0점 처리된다.',
      },
      {
        id: 'ps.scaleup',
        label: '(C) Scale-up 준비',
        max: 5,
        points: [0, 2, 5],
        levelGuide:
          'level 0 = 양산/조달/인증 계획이 확인되지 않음. ' +
          'level 1 = 계획은 있으나 계약·설비 등 실체적 근거가 부족. ' +
          'level 2 = 양산 라인·파운드리 계약·원료 조달·인증 로드맵 중 복수가 실체적으로 확인.',
      },
    ],
  },
};

export const TOTAL_MAX = PRINCIPLE_ORDER.reduce((s, p) => s + RUBRIC[p].max, 0); // 100

/* ------------------------------------------------------------------ *
 * Cut-off 규칙
 * ------------------------------------------------------------------ */

export const CUTOFF = {
  passScore: 70,
  bands: [
    { min: 85, band: 'high_conviction' as const, label: 'High-conviction fast-track' },
    { min: 70, band: 'standard_ic' as const, label: 'Standard IC 진행' },
    { min: 60, band: 'watchlist' as const, label: 'Watchlist (특정 Gate 보완 조건부 재검토)' },
    { min: 0, band: 'reject' as const, label: 'Reject' },
  ],
} as const;

export type Band = (typeof CUTOFF.bands)[number]['band'];

/** level → 점수 변환 (범위 밖 level은 clamp) */
export function scoreForLevel(spec: CriterionSpec, level: number): number {
  const idx = Math.max(0, Math.min(spec.points.length - 1, Math.round(level)));
  return spec.points[idx];
}

export function findCriterion(principle: PrincipleId, criterionId: string) {
  return RUBRIC[principle].criteria.find((c) => c.id === criterionId);
}
