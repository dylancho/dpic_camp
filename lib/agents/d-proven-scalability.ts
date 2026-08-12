/**
 * 원칙 d — Proven Scalability (기술성, 25점)   ★ 담당: 조원 D
 *
 * "실험이 아니라, 실제로 구현되며 해당 팀만이 가진 해자여야 한다."
 *
 * 주의: 이 원칙은 (A) 1개 이상 · (B) 2개 이상이 **필수 조건**이다.
 *       미충족 시 세부 점수와 무관하게 원칙 전체가 0점 처리된다 (lib/scoring.ts가 강제).
 *       따라서 gateSignals.provenWorkingCount / moatCount를 정확히 채우는 것이 이 에이전트의 핵심 책임.
 */

import type { PrincipleAgent } from '../contract';
import { runPrincipleAgent } from './runtime';

const EXTRA_GUIDANCE = `
## (A) 기술 작동 증명 — ps.working, level = 충족 개수(0~3)
a. 서로 다른 고객·환경에서 PoC ≥2회 **AND** 핵심 성능 KPI가 ±10~20% 내 재현.
   → "재현"이 핵심이다. 한 사이트에서 두 번은 불충족. 편차 수치가 없으면 불충족.
b. 제3자 시험성적서 · 독립 인증 ≥2건.
   → **Founder 자체 테스트만 있으면 불인정.** 발급 기관명이 확인되어야 한다.
     (KTL, KTR, KCL, TÜV, SGS, 대학 산학협력단, 공인시험기관 등)
c. 하드웨어·산업기술의 실환경 누적 가동 ≥1,000시간.
   → ★ Calibration의 workingProof 임계치를 우선 적용한다. 원천기술(deep tech) 아키타입이면
     이 1,000시간 기준을 그대로 적용하지 말고 pilot plant 가동 + 제3자 검증 ≥2로 대체 판단한다.
     SW·AI 아키타입이면 서로 다른 환경 배포 ≥2 + 성능 재현으로 본다.

gateSignals.provenWorkingCount에 충족 개수를 담는다. 0이면 이 원칙은 0점이 되므로
그 판단을 rationale에 명확히 남겨라 (IC에서 가장 먼저 반박당하는 지점이다).

## (B) 해자 Defensibility — ps.moat, level = 충족 개수(0~4)
a. 거래소 기술성 평가 A 이상 (기술특례상장 기준 등급). AA/A만 인정, BBB 이하는 불충족.
   평가 자체를 안 받았으면 불충족(미실시와 낮은 등급을 구분해 rationale에 적을 것).
b. 등록 특허 — **출원(application)과 등록(registration)을 반드시 구분한다.**
   "특허 30건 출원"은 해자가 아니다. 등록 건수가 Calibration의 patentCountFloor 이상이고,
   핵심 청구항이 경쟁사 회피가 어려운 구조(물질/조성 청구항, 필수 공정 파라미터 범위 등)인지 본다.
   건수만 많고 청구항이 좁으면 partial로 낮춘다.
c. 관련 도메인 석사 이상 인력 비중 ≥60%. 전체 인원 대비 비율이 확인되어야 한다.
   (연구인력 수만 나오고 전체 인원이 없으면 계산 불가 → unknown)
d. 핵심 인력의 랩실 근무 이력 또는 해당 기술에 관한 peer-reviewed 논문·핵심 특허 보유.

gateSignals.moatCount에 충족 개수를 담는다. 2 미만이면 이 원칙 전체가 0점 처리된다.

## (C) Scale-up 준비 — ps.scaleup
양산 라인 증설, 파운드리·CMO 계약, 원료(feedstock) 장기 조달 계약, 규제 인증 로드맵,
CapEx 조달 계획 중 **실체적 근거가 있는 것**을 센다. "계획 중"은 level 1을 넘지 못한다.

## 공통
"세계 최초", "독보적 기술력" 같은 보도자료 표현은 근거가 아니다.
기술 난이도가 높다는 사실 자체도 해자가 아니다 — 경쟁사가 회피 못 하는 구조인지만 본다.
`.trim();

export const provenScalabilityAgent: PrincipleAgent = (input) =>
  runPrincipleAgent('proven_scalability', input, { extraGuidance: EXTRA_GUIDANCE });
