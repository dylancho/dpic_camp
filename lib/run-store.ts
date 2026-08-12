/**
 * 심사 1건 = runs/<slug>/ 디렉터리 하나.
 * 오케스트레이터(스킬)와 서브에이전트들이 이 디렉터리를 통해 데이터를 주고받는다.
 *
 *   runs/<slug>/
 *     evidence.md            ← 4개 에이전트가 공유하는 근거 (읽기 전용)
 *     evidence.json
 *     calibration.json       ← STEP 0 산출물
 *     findings-<원칙>.json   ← 각 서브에이전트가 쓴다
 *     scorecard.md           ← 채점 결과 (코드가 쓴다)
 *     verdict.json
 *     report.md              ← 최종 투자보고서
 */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

export function slugify(name: string) {
  return name.trim().replace(/\s+/g, '-').replace(/[\\/:*?"<>|]/g, '');
}

export function runDir(name: string) {
  return path.join('runs', slugify(name));
}

export function readJson<T>(file: string): T | null {
  if (!existsSync(file)) return null;
  return JSON.parse(readFileSync(file, 'utf8')) as T;
}
