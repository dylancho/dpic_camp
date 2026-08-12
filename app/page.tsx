'use client';

import { useRef, useState } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Calibration, FinalVerdict, PipelineEvent, ScoredPrinciple } from '@/lib/contract';
import { PRINCIPLE_META, PRINCIPLE_ORDER, type PrincipleId } from '@/lib/philosophy';

type StageState = Record<string, 'idle' | 'start' | 'done' | 'error'>;

const STAGES: { key: string; label: string }[] = [
  { key: 'evidence', label: 'STEP 0-A · 근거 수집' },
  { key: 'calibration', label: 'STEP 0-B · 임계치 확정' },
  { key: 'principles', label: 'STEP 1 · 원칙 에이전트 4개' },
  { key: 'cutoff', label: 'STEP 2 · 채점 & Cut-off' },
  { key: 'report', label: 'STEP 3 · 보고서 작성' },
];

export default function Page() {
  const [name, setName] = useState('');
  const [underwriter, setUnderwriter] = useState('');
  const [notes, setNotes] = useState('');
  const [running, setRunning] = useState(false);

  const [stages, setStages] = useState<StageState>({});
  const [stageDetail, setStageDetail] = useState<Record<string, string>>({});
  const [sources, setSources] = useState<{ id: string; source: string; title: string; url?: string }[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);
  const [calibration, setCalibration] = useState<{ c: Calibration; name: string } | null>(null);
  const [scored, setScored] = useState<ScoredPrinciple[]>([]);
  const [verdict, setVerdict] = useState<FinalVerdict | null>(null);
  const [report, setReport] = useState('');
  const [error, setError] = useState('');
  const reportRef = useRef<HTMLDivElement>(null);

  async function run() {
    if (!name.trim() || running) return;
    setRunning(true);
    setStages({});
    setStageDetail({});
    setSources([]);
    setGaps([]);
    setCalibration(null);
    setScored([]);
    setVerdict(null);
    setReport('');
    setError('');

    try {
      const res = await fetch('/api/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), underwriter: underwriter.trim() || undefined, notes: notes.trim() || undefined }),
      });
      if (!res.ok || !res.body) throw new Error((await res.json().catch(() => ({}))).error ?? '요청 실패');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.trim()) continue;
          const ev = JSON.parse(line) as PipelineEvent;
          apply(ev);
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  function apply(ev: PipelineEvent) {
    switch (ev.type) {
      case 'stage':
        setStages((s) => ({ ...s, [ev.stage]: ev.status }));
        if (ev.detail) setStageDetail((d) => ({ ...d, [ev.stage]: ev.detail! }));
        break;
      case 'evidence':
        setSources(ev.sources);
        setGaps(ev.gaps);
        break;
      case 'calibration':
        setCalibration({ c: ev.calibration, name: ev.archetypeName });
        break;
      case 'principle':
        setScored((prev) => [...prev.filter((p) => p.principle !== ev.result.principle), ev.result]);
        break;
      case 'verdict':
        setVerdict(ev.verdict);
        break;
      case 'report_delta':
        setReport((r) => r + ev.text);
        reportRef.current?.scrollTo({ top: reportRef.current.scrollHeight });
        break;
      case 'error':
        setError(ev.message);
        break;
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">양양 5조 · Pre-IPO 투자보고서 에이전트</h1>
        <p className="mt-2 text-sm leading-relaxed text-neutral-600">
          우리는 임팩트에 투자하지만, 임팩트라는 이유로 투자하지 않습니다.
          <br />
          구조적 수요 · 검증된 기술 · 고객 손익 · 측정 가능한 임팩트가 만나는 지점에만 투자합니다.
        </p>
      </header>

      {/* 입력 */}
      <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-medium text-neutral-700">기업명 *</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="예: 에스그래핀"
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-900"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-neutral-700">주관사</span>
            <input
              value={underwriter}
              onChange={(e) => setUnderwriter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="예: 미래에셋증권"
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-900"
            />
          </label>
        </div>
        <label className="mt-3 block">
          <span className="text-xs font-medium text-neutral-700">
            참고 자료 붙여넣기 (IR 자료 · 기사 · 기술문서 — 있을수록 근거 기반 판정이 정확해집니다)
          </span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={5}
            className="mt-1 w-full resize-y rounded-lg border border-neutral-300 px-3 py-2 font-mono text-xs outline-none focus:border-neutral-900"
          />
        </label>
        <button
          onClick={run}
          disabled={running || !name.trim()}
          className="mt-4 rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-300"
        >
          {running ? '심사 중…' : '투자보고서 생성'}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">오류: {error}</p>}
      </section>

      {/* 파이프라인 진행 */}
      {(running || scored.length > 0) && (
        <section className="mt-6 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold">파이프라인</h2>
          <ol className="grid gap-2 sm:grid-cols-5">
            {STAGES.map((s) => {
              const st = stages[s.key] ?? 'idle';
              return (
                <li
                  key={s.key}
                  className={`rounded-lg border px-3 py-2 text-xs ${
                    st === 'done'
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : st === 'start'
                        ? 'border-amber-200 bg-amber-50 text-amber-800'
                        : 'border-neutral-200 bg-neutral-50 text-neutral-400'
                  }`}
                >
                  <div className="font-medium">{s.label}</div>
                  {stageDetail[s.key] && <div className="mt-0.5 opacity-80">{stageDetail[s.key]}</div>}
                </li>
              );
            })}
          </ol>

          {sources.length > 0 && (
            <details className="mt-4">
              <summary className="cursor-pointer text-xs font-medium text-neutral-700">
                수집된 근거 {sources.length}건 {gaps.length > 0 && `· 공백 ${gaps.length}건`}
              </summary>
              <ul className="mt-2 space-y-1 text-xs text-neutral-600">
                {sources.map((s) => (
                  <li key={s.id}>
                    <code className="rounded bg-neutral-100 px-1">{s.id}</code>{' '}
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer" className="underline">
                        {s.title}
                      </a>
                    ) : (
                      s.title
                    )}
                  </li>
                ))}
              </ul>
              {gaps.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-amber-700">
                  {gaps.map((g, i) => (
                    <li key={i}>⚠ {g}</li>
                  ))}
                </ul>
              )}
            </details>
          )}
        </section>
      )}

      {/* STEP 0 임계치 */}
      {calibration && (
        <section className="mt-6 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold">
            STEP 0 · Threshold Calibration — <span className="text-neutral-500">{calibration.name}</span>
          </h2>
          <p className="mt-1 text-xs text-neutral-600">{calibration.c.classificationRationale}</p>
          <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
            {[
              ['작동 증명 임계치', calibration.c.thresholds.workingProof],
              ['상업 증거 임계치', calibration.c.thresholds.commercialEvidence],
              ['cost 단위', calibration.c.thresholds.costUnit],
              ['impact 단위', calibration.c.thresholds.impactUnit],
              ['고객 payback 임계', `${calibration.c.thresholds.paybackThresholdYears}년`],
              ['등록특허 하한', `${calibration.c.thresholds.patentCountFloor}건`],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg bg-neutral-50 px-3 py-2">
                <dt className="text-[11px] text-neutral-500">{k}</dt>
                <dd className="mt-0.5 text-neutral-800">{v}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* 스코어 카드 */}
      {scored.length > 0 && (
        <section className="mt-6 grid gap-3 sm:grid-cols-2">
          {PRINCIPLE_ORDER.map((id: PrincipleId) => {
            const p = scored.find((x) => x.principle === id);
            const meta = PRINCIPLE_META[id];
            if (!p)
              return (
                <div key={id} className="animate-pulse rounded-xl border border-neutral-200 bg-white p-5">
                  <div className="text-sm font-medium text-neutral-400">
                    {meta.key}. {meta.name} 심사 중…
                  </div>
                </div>
              );
            const ratio = p.score / p.max;
            return (
              <div key={id} className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
                <div className="flex items-baseline justify-between">
                  <h3 className="text-sm font-semibold">
                    {meta.key}. {p.name}{' '}
                    <span className="font-normal text-neutral-400">· {p.category} · {meta.owner}</span>
                  </h3>
                  <span className="text-lg font-semibold tabular-nums">
                    {p.score}
                    <span className="text-sm font-normal text-neutral-400">/{p.max}</span>
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-neutral-100">
                  <div
                    className={`h-1.5 rounded-full ${ratio >= 0.6 ? 'bg-emerald-500' : 'bg-red-400'}`}
                    style={{ width: `${Math.max(2, ratio * 100)}%` }}
                  />
                </div>
                {p.zeroedReason && <p className="mt-2 text-xs text-red-600">⛔ {p.zeroedReason}</p>}
                {p.belowFloor && !p.zeroedReason && (
                  <p className="mt-2 text-xs text-amber-700">⚠ floor({p.floor}) 미달 → IC 특별승인 대상</p>
                )}
                <p className="mt-2 text-xs leading-relaxed text-neutral-600">{p.findings.summary}</p>
                <ul className="mt-3 space-y-1 text-[11px] text-neutral-600">
                  {p.criteria.map((c) => (
                    <li key={c.criterionId} className="flex justify-between gap-2">
                      <span className="truncate">{c.label}</span>
                      <span className="shrink-0 tabular-nums text-neutral-400">
                        {c.score}/{c.max} ({c.verdict})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </section>
      )}

      {/* 최종 판정 */}
      {verdict && (
        <section
          className={`mt-6 rounded-xl border p-5 shadow-sm ${
            verdict.hardGateFailed
              ? 'border-red-200 bg-red-50'
              : verdict.pass
                ? 'border-emerald-200 bg-emerald-50'
                : 'border-amber-200 bg-amber-50'
          }`}
        >
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-semibold tabular-nums">{verdict.total}</span>
            <span className="text-neutral-500">/ {verdict.max}</span>
            <span className="ml-auto text-sm font-medium">{verdict.bandLabel}</span>
          </div>
          {verdict.gateNotes.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs">
              {verdict.gateNotes.map((n, i) => (
                <li key={i}>• {n}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* 보고서 */}
      {report && (
        <section className="mt-6 rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">투자보고서</h2>
            <button
              onClick={() => navigator.clipboard.writeText(report)}
              className="rounded-md border border-neutral-300 px-3 py-1 text-xs hover:bg-neutral-50"
            >
              마크다운 복사
            </button>
          </div>
          <div
            ref={reportRef}
            className="prose-sm max-h-[70vh] overflow-y-auto text-sm leading-relaxed
                       [&_h2]:mt-6 [&_h2]:border-t [&_h2]:border-neutral-100 [&_h2]:pt-4 [&_h2]:text-base [&_h2]:font-semibold
                       [&_h3]:mt-4 [&_h3]:font-semibold
                       [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5
                       [&_p]:my-2 [&_strong]:font-semibold
                       [&_table]:my-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs
                       [&_td]:border [&_td]:border-neutral-200 [&_td]:px-2 [&_td]:py-1
                       [&_th]:border [&_th]:border-neutral-200 [&_th]:bg-neutral-50 [&_th]:px-2 [&_th]:py-1
                       [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
          >
            <Markdown remarkPlugins={[remarkGfm]}>{report}</Markdown>
          </div>
        </section>
      )}
    </main>
  );
}
