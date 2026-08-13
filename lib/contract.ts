/**
 * ★★★ 조원 4명 사이의 계약서 (Interface Contract) ★★★
 *
 * 이 파일만 지키면 4명이 서로의 코드를 안 보고 병렬로 개발할 수 있다.
 * 각 원칙 에이전트는 결국 아래 한 줄짜리 함수 시그니처다:
 *
 *     type PrincipleAgent = (input: AgentInput) => Promise<PrincipleFindings>
 *
 * 규칙 3가지:
 *   1. 에이전트는 **점수를 매기지 않는다**. level(이산 판정)만 낸다. 점수는 scoring/score.ts가 계산.
 *   2. 모든 판정에는 evidence(원문 인용 + 출처 id)가 붙어야 한다. 인용 없는 주장은 unknown 처리.
 *   3. 근거가 없으면 지어내지 말고 verdict='unknown' + missingData에 "무엇이 없었는지"를 남긴다.
 */

import { z } from 'zod';
import type { PrincipleId } from './philosophy';
import type { ArchetypeId } from './archetypes';

/* ------------------------------------------------------------------ *
 * 1. 입력 — 회사 & 증거
 * ------------------------------------------------------------------ */

export const CompanyInputSchema = z.object({
  /** 기업명 (필수) */
  name: z.string().min(1),
  /** 주관사 (IPO 대표주관사) */
  underwriter: z.string().optional(),
  /** 사용자가 직접 붙여넣은 IR 자료 / 뉴스 / 기술문서 원문 */
  notes: z.string().optional(),
  /** 참고 URL */
  urls: z.array(z.string()).optional(),
  /** DART 고유번호 8자리. 동명이인이 있을 때 어느 법인인지 못박는다 */
  corpCode: z.string().optional(),
  /** 영문 상호 등 별칭. 웹 검색 관련성 필터가 이것도 함께 본다 (에스그래핀 ↔ S-Graphene) */
  aliases: z.array(z.string()).optional(),
});
export type CompanyInput = z.infer<typeof CompanyInputSchema>;

/** 증거 1건. 모든 어댑터(DART/웹/사용자 입력)가 이 형태로 정규화된다. */
export const EvidenceItemSchema = z.object({
  /** 인용 시 사용하는 짧은 id. 예: "dart-1", "web-3", "note-1" */
  id: z.string(),
  source: z.enum(['dart', 'web', 'user_note', 'patent', 'model_prior']),
  title: z.string(),
  url: z.string().optional(),
  /** 공시일/기사일 (YYYY-MM-DD) */
  date: z.string().optional(),
  /** 본문 (에이전트 프롬프트에 들어가는 실제 텍스트) */
  content: z.string(),
});
export type EvidenceItem = z.infer<typeof EvidenceItemSchema>;

export type EvidencePack = {
  company: CompanyInput;
  items: EvidenceItem[];
  /** 수집 과정에서 실패하거나 비어 있던 소스 — 보고서 신뢰도 섹션에 노출된다 */
  gaps: string[];
};

/* ------------------------------------------------------------------ *
 * 2. STEP 0 — Threshold Calibration 산출물
 * ------------------------------------------------------------------ */

export const CalibrationSchema = z.object({
  primaryArchetype: z.enum([
    'deep_tech',
    'materials',
    'industrial_hardware',
    'energy_infra',
    'recycling',
    'sw_ai_robotics',
  ]),
  secondaryArchetype: z
    .enum([
      'deep_tech',
      'materials',
      'industrial_hardware',
      'energy_infra',
      'recycling',
      'sw_ai_robotics',
    ])
    .nullable(),
  /** 어떤 아키타입에도 딱 맞지 않을 때의 조정 근거 1문장 (규칙상 필수) */
  classificationRationale: z.string(),
  /** 이 기업에 적용할 정량 임계치 — 스코어링 상단에 반드시 출력된다 */
  thresholds: z.object({
    workingProof: z.string().describe('작동 증명 임계치. 예: "실환경 누적 가동 ≥1,000h + uptime ≥95%"'),
    commercialEvidence: z.string().describe('상업 증거 임계치. 예: "binding PO ≥2건"'),
    costUnit: z.string().describe('핵심 cost 단위. 예: "$/kg"'),
    impactUnit: z.string().describe('핵심 impact 단위(Primary Impact Unit 후보). 예: "tCO2e/ton-제품"'),
    paybackThresholdYears: z.number().describe('고객 payback 임계 연수. SW면 CAC payback(년) 환산.'),
    patentCountFloor: z.number().int().describe('해자 인정 등록특허 건수 하한 (소재·장비 3~5건 등)'),
  }),
  /** 이 아키타입에서 특히 무겁게/가볍게 볼 항목 — 원칙 에이전트 프롬프트에 주입된다 */
  weightingNotes: z.array(z.string()),
});
export type Calibration = z.infer<typeof CalibrationSchema>;

/* ------------------------------------------------------------------ *
 * 3. 원칙 에이전트의 출력 (★ 조원들이 반드시 맞춰야 하는 형태)
 * ------------------------------------------------------------------ */

export const EvidenceRefSchema = z.object({
  /** EvidencePack.items[].id 를 그대로 쓴다. 없는 id를 쓰면 검증에서 걸러진다. */
  sourceId: z.string(),
  /** 원문 그대로의 인용 (요약 금지, 300자 이내) */
  quote: z.string(),
});
export type EvidenceRef = z.infer<typeof EvidenceRefSchema>;

export const CriterionFindingSchema = z.object({
  /** RUBRIC의 criterion id. 예: "pi.unit" */
  criterionId: z.string(),
  /** 루브릭 levelGuide가 정의한 이산 레벨 */
  level: z.number().int().min(0).max(4),
  verdict: z.enum(['met', 'partial', 'unmet', 'unknown']),
  /** 왜 이 level인지 2~4문장. 임계치(calibration)를 명시적으로 참조할 것. */
  rationale: z.string(),
  evidence: z.array(EvidenceRefSchema),
});
export type CriterionFinding = z.infer<typeof CriterionFindingSchema>;

/** 게이트 엔진이 읽는 구조화 신호. 원칙마다 채우는 필드가 다르다. */
export const GateSignalsSchema = z.object({
  /** [c] Primary Impact Unit이 정의되었는가 — 하드 게이트 */
  primaryImpactUnit: z.string().nullable().optional(),
  /** [a] 확인된 구조적 driver 목록 */
  structuralDrivers: z
    .array(
      z.enum([
        'resource_constraint',
        'cost_curve_shift',
        'infrastructure_replacement',
        'supply_chain_reconfiguration',
        'productivity_imperative',
      ]),
    )
    .optional(),
  /** [b] 인정된 상업 증거 건수 (MOU/LOI 제외) */
  paidEvidenceCount: z.number().int().optional(),
  /** [d] (A) 작동 증명 충족 개수 — 1 미만이면 원칙 0점 */
  provenWorkingCount: z.number().int().optional(),
  /** [d] (B) 해자 충족 개수 — 2 미만이면 원칙 0점 */
  moatCount: z.number().int().optional(),
});
export type GateSignals = z.infer<typeof GateSignalsSchema>;

export const PrincipleFindingsSchema = z.object({
  criteria: z.array(CriterionFindingSchema),
  gateSignals: GateSignalsSchema,
  /** 투자 판단을 뒤집을 수 있는 위험 신호 */
  redFlags: z.array(z.string()),
  /** 확인하지 못한 데이터 — "무엇을 더 받아야 판단이 바뀌는가" */
  missingData: z.array(z.string()),
  /** IC에서 반드시 물어야 할 질문 (킬 퀘스천) */
  killQuestions: z.array(z.string()),
  /** 0~1. 증거 기반이 얇으면 낮춘다. */
  confidence: z.number().min(0).max(1),
  /** 이 원칙에 대한 2~3문장 요약 */
  summary: z.string(),
  /**
   * 담당 조원의 스킬이 정의한 출력 형식(표·서사)을 그대로 채운 마크다운.
   * 최종 투자보고서의 해당 원칙 섹션에 그대로 실린다.
   * level만으로는 IC에서 설명이 안 되므로, 판정의 서술 근거를 여기에 남긴다.
   */
  skillReport: z.string().optional(),
  /**
   * 에이전트가 조사 중 새로 찾은 근거. 채점 전에 EvidencePack에 편입되어야
   * 인용이 유효해진다 (없는 sourceId 인용은 sanitizeEvidence가 버린다).
   */
  extraEvidence: z.array(EvidenceItemSchema).optional(),
});
export type PrincipleFindings = z.infer<typeof PrincipleFindingsSchema>;

/* ------------------------------------------------------------------ *
 * 4. 채점 후 산출물
 * ------------------------------------------------------------------ */

export type ScoredCriterion = {
  criterionId: string;
  label: string;
  max: number;
  level: number;
  score: number;
  verdict: CriterionFinding['verdict'];
  rationale: string;
  evidence: EvidenceRef[];
};

export type ScoredPrinciple = {
  principle: PrincipleId;
  name: string;
  category: string;
  max: number;
  /** 게이트 적용 전 원점수 */
  rawScore: number;
  /** 게이트(필수조건 미충족 → 0점) 적용 후 최종 점수 */
  score: number;
  /** 편중 방지 floor (max * 0.6) */
  floor: number;
  belowFloor: boolean;
  zeroedReason?: string;
  criteria: ScoredCriterion[];
  findings: PrincipleFindings;
};

export type FinalVerdict = {
  total: number;
  max: number;
  band: 'high_conviction' | 'standard_ic' | 'watchlist' | 'reject';
  bandLabel: string;
  pass: boolean;
  /** 하드 게이트 탈락 여부 (Primary Impact Unit 미정의) */
  hardGateFailed: boolean;
  /** 위반된 규칙들 — 보고서 상단에 그대로 노출 */
  gateNotes: string[];
  /** floor 미달로 IC 특별승인 대상인 원칙들 */
  needsICApproval: PrincipleId[];
};

/* ------------------------------------------------------------------ *
 * 5. 에이전트 시그니처 — 조원 4명이 각자 구현하는 것
 * ------------------------------------------------------------------ */

export type AgentInput = {
  company: CompanyInput;
  calibration: Calibration;
  evidence: EvidencePack;
};

export type PrincipleAgent = (input: AgentInput) => Promise<PrincipleFindings>;

/* ------------------------------------------------------------------ *
 * 6. 오케스트레이터 → UI 스트리밍 이벤트 (NDJSON)
 * ------------------------------------------------------------------ */

export type PipelineEvent =
  | { type: 'stage'; stage: string; status: 'start' | 'done' | 'error'; detail?: string }
  | { type: 'evidence'; count: number; sources: { id: string; source: string; title: string; url?: string }[]; gaps: string[] }
  | { type: 'calibration'; calibration: Calibration; archetypeName: string }
  | { type: 'principle'; result: ScoredPrinciple }
  | { type: 'verdict'; verdict: FinalVerdict }
  | { type: 'report_delta'; text: string }
  | { type: 'done' }
  | { type: 'error'; message: string };
