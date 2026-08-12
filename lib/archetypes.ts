/**
 * STEP 0 — Threshold Calibration 용 아키타입 표.
 *
 * 스코어링 **전에 반드시** 수행한다. 대상 기업을 아래 아키타입 중 하나(또는 혼합)로 분류하고,
 * 각 원칙의 정량 임계치를 그 아키타입 기준으로 설정한 뒤 명시한다.
 * 어떤 아키타입에도 딱 맞지 않으면 가장 가까운 것을 기준으로 조정하고 근거를 1문장으로 남긴다.
 *
 * 규칙:
 *  (a) 하드웨어·소재는 가동시간·재현성을 무겁게, SW는 고객 수·retention을 무겁게 본다.
 *  (b) 원천기술은 상업화 타임라인이 길다는 점을 반영해 "가동 1,000시간" 같은 하드웨어 기준을
 *      그대로 적용하지 않는다.
 *  (c) 설정한 임계치와 그 근거를 스코어링 상단에 반드시 출력한다.
 */

export type ArchetypeId =
  | 'deep_tech'
  | 'materials'
  | 'industrial_hardware'
  | 'energy_infra'
  | 'recycling'
  | 'sw_ai_robotics';

export type Archetype = {
  id: ArchetypeId;
  name: string;
  examples: string;
  /** 작동 증명 임계치 (예시 앵커) */
  workingProofAnchor: string;
  /** 상업 증거 앵커 */
  commercialAnchor: string;
  /** 핵심 cost/impact 단위 */
  costImpactUnits: string;
  /** 가중 관점 — (a)(b) 규칙의 반영 */
  weightingNote: string;
};

export const ARCHETYPES: Record<ArchetypeId, Archetype> = {
  deep_tech: {
    id: 'deep_tech',
    name: '원천기술 · Deep Tech',
    examples: '플라즈마 등 (ex. EN2CORE)',
    workingProofAnchor: 'Pilot plant 가동 + 제3자 검증 ≥2 / TRL 6+ / 장기 validation 허용',
    commercialAnchor: 'Paid pilot·개발계약, offtake LOI→계약 전환',
    costImpactUnits: '$/ton, tCO2e/unit',
    weightingNote:
      '상업화 타임라인이 길다. "실환경 누적 가동 1,000시간" 같은 하드웨어 기준을 그대로 적용하지 말고, ' +
      'pilot plant 가동 실적과 제3자 검증으로 대체 판단한다.',
  },
  materials: {
    id: 'materials',
    name: '소재 · Materials',
    examples: 'ex. Phoenix Tailings, S-Graphene',
    workingProofAnchor: 'Pilot run ≥2 + 고객 qualification ≥1 / 재현성 ±10~20%',
    commercialAnchor: '반복 구매·qualification, 수주잔고',
    costImpactUnits: '$/kg, yield%, purity',
    weightingNote: '고객 qualification 통과 여부가 사실상 관문이다. 재현성(편차)을 무겁게 본다.',
  },
  industrial_hardware: {
    id: 'industrial_hardware',
    name: '산업 장비 · Hardware',
    examples: '공정 장비, 산업용 설비',
    workingProofAnchor: 'Paid PoC ≥2 / 실환경 가동 ≥1,000h / uptime',
    commercialAnchor: 'PO·binding contract ≥2',
    costImpactUnits: 'Payback yr, $/unit',
    weightingNote: '가동시간·uptime을 무겁게 본다. 고객 payback 연수가 구매 의사결정의 핵심.',
  },
  energy_infra: {
    id: 'energy_infra',
    name: '에너지 · 인프라',
    examples: 'ex. JR Energy, CTR',
    workingProofAnchor: '실증 사이트 가동 + 성능보증(PPA/성능계약)',
    commercialAnchor: '장기계약·offtake, 계약부채',
    costImpactUnits: '$/kWh, MWh',
    weightingNote: '성능보증 계약 구조와 장기 offtake의 구속력을 무겁게 본다.',
  },
  recycling: {
    id: 'recycling',
    name: '리사이클 · 자원회수',
    examples: '폐배터리·폐촉매·스크랩 회수',
    workingProofAnchor: '파일럿 recovery rate 검증 ≥2',
    commercialAnchor: 'Feedstock 확보 + offtake',
    costImpactUnits: 'recovery%, $/ton',
    weightingNote: 'feedstock(투입 원료) 확보가 병목이다. 회수율 재현성과 조달 계약을 함께 본다.',
  },
  sw_ai_robotics: {
    id: 'sw_ai_robotics',
    name: 'SW · AI · 로보틱스',
    examples: 'ex. Neubility',
    workingProofAnchor: '서로 다른 환경 배포 ≥2 / 성능 재현',
    commercialAnchor: '유료 고객 ≥5, retention',
    costImpactUnits: 'GM%, CAC payback',
    weightingNote: '고객 수·retention을 무겁게 본다. 가동시간 기준은 적용하지 않는다.',
  },
};

export const ARCHETYPE_TABLE_MD = `
| 아키타입 | 작동 증명 임계치(예시 앵커) | 상업 증거 앵커 | 핵심 cost/impact 단위 |
|---|---|---|---|
${Object.values(ARCHETYPES)
  .map(
    (a) =>
      `| ${a.name} (${a.examples}) | ${a.workingProofAnchor} | ${a.commercialAnchor} | ${a.costImpactUnits} |`,
  )
  .join('\n')}
`.trim();
