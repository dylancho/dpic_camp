/**
 * ★ 오케스트레이션 에이전트 (담당: 나)
 *
 * 파이프라인:
 *   STEP 0-A  Evidence Pack 수집     (DART · 웹 · 사용자 입력 → 하나의 공유 근거 풀)
 *   STEP 0-B  Threshold Calibration  (아키타입 분류 → 정량 임계치 확정)  ※ 스코어링 전 필수
 *   STEP 1    원칙 에이전트 4개 병렬  (동일 EvidencePack + 동일 임계치 주입)
 *   STEP 2    결정론적 채점 + Cut-off (LLM 없음)
 *   STEP 3    보고서 작성 스트리밍
 *
 * 설계 포인트 3가지:
 *  1) 근거는 한 번만 모아 4명이 공유한다 → 점수 합산이 의미를 갖는다.
 *  2) 임계치는 스코어링 전에 확정한다 → 4명이 같은 잣대로 채점한다.
 *  3) 채점은 코드가 한다 → 같은 findings면 항상 같은 점수. IC에서 방어 가능.
 */

import { PRINCIPLE_ORDER, type PrincipleId } from '../philosophy';
import type { AgentInput, CompanyInput, PipelineEvent, PrincipleAgent, PrincipleFindings, ScoredPrinciple } from '../contract';
import { buildEvidencePack } from '../evidence/pack';
import { applyCutoff, scorePrinciple } from '../scoring';
import { archetypeName, calibrateThresholds } from './calibrate';
import { streamReport } from './report-writer';

import { structuralDemandAgent } from './a-structural-demand';
import { economicValueAgent } from './b-economic-value';
import { physicalImpactAgent } from './c-physical-impact';
import { provenScalabilityAgent } from './d-proven-scalability';

/** 새 에이전트를 붙일 때 여기만 갈아끼우면 된다 */
export const AGENTS: Record<PrincipleId, PrincipleAgent> = {
  structural_demand: structuralDemandAgent,
  economic_value: economicValueAgent,
  physical_impact: physicalImpactAgent,
  proven_scalability: provenScalabilityAgent,
};

/** 에이전트 하나가 죽어도 파이프라인 전체를 죽이지 않는다 (데모 안정성) */
function fallbackFindings(reason: string): PrincipleFindings {
  return {
    criteria: [],
    gateSignals: {},
    redFlags: [`에이전트 실행 실패로 이 원칙은 0점 처리되었습니다: ${reason}`],
    missingData: ['에이전트 실행 실패 — 재실행 필요'],
    killQuestions: [],
    confidence: 0,
    summary: `실행 실패: ${reason}`,
  };
}

export async function* runPipeline(company: CompanyInput): AsyncGenerator<PipelineEvent> {
  try {
    /* ── STEP 0-A: Evidence Pack ───────────────────────────────── */
    yield { type: 'stage', stage: 'evidence', status: 'start', detail: 'DART · 웹 · 제출 자료 수집' };
    const evidence = await buildEvidencePack(company);
    yield {
      type: 'evidence',
      count: evidence.items.length,
      sources: evidence.items.map((i) => ({ id: i.id, source: i.source, title: i.title, url: i.url })),
      gaps: evidence.gaps,
    };
    yield { type: 'stage', stage: 'evidence', status: 'done', detail: `근거 ${evidence.items.length}건` };

    /* ── STEP 0-B: Threshold Calibration ──────────────────────── */
    yield { type: 'stage', stage: 'calibration', status: 'start', detail: '아키타입 분류 · 임계치 확정' };
    const calibration = await calibrateThresholds(company, evidence);
    yield { type: 'calibration', calibration, archetypeName: archetypeName(calibration) };
    yield { type: 'stage', stage: 'calibration', status: 'done', detail: archetypeName(calibration) };

    const input: AgentInput = { company, calibration, evidence };

    /* ── STEP 1: 원칙 에이전트 4개 병렬 ───────────────────────── */
    yield { type: 'stage', stage: 'principles', status: 'start', detail: '원칙 에이전트 4개 병렬 실행' };

    // 먼저 끝나는 순서대로 UI에 흘려보내기 위해 Promise를 개별로 태그한다
    const tagged = PRINCIPLE_ORDER.map((id) =>
      AGENTS[id](input)
        .then((findings) => ({ id, findings }))
        .catch((e: unknown) => ({ id, findings: fallbackFindings((e as Error).message) })),
    );

    const scored: ScoredPrinciple[] = [];
    const pending = new Set(tagged);
    while (pending.size) {
      const done = await Promise.race([...pending].map((p) => p.then((r) => ({ p, r }))));
      pending.delete(done.p);
      const s = scorePrinciple(done.r.id, done.r.findings, evidence);
      scored.push(s);
      yield { type: 'principle', result: s };
    }
    scored.sort((a, b) => PRINCIPLE_ORDER.indexOf(a.principle) - PRINCIPLE_ORDER.indexOf(b.principle));
    yield { type: 'stage', stage: 'principles', status: 'done' };

    /* ── STEP 2: 결정론적 Cut-off ─────────────────────────────── */
    yield { type: 'stage', stage: 'cutoff', status: 'start', detail: '하드 게이트 · 필수조건 · Floor 적용' };
    const verdict = applyCutoff(scored);
    yield { type: 'verdict', verdict };
    yield { type: 'stage', stage: 'cutoff', status: 'done', detail: `${verdict.total}/100 · ${verdict.bandLabel}` };

    /* ── STEP 3: 보고서 ───────────────────────────────────────── */
    yield { type: 'stage', stage: 'report', status: 'start', detail: '투자보고서 작성' };
    const result = streamReport({ company, calibration, scored, verdict, evidence });
    for await (const delta of result.textStream) {
      yield { type: 'report_delta', text: delta };
    }
    yield { type: 'stage', stage: 'report', status: 'done' };
    yield { type: 'done' };
  } catch (e) {
    yield { type: 'error', message: (e as Error).message };
  }
}
