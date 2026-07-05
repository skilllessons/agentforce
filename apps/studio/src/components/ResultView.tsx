'use client'

import clsx from 'clsx'
import type { ResearchOutput } from '@/lib/types'

const CONF_COLOR = {
  high: 'bg-emerald-100 text-emerald-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-rose-100 text-rose-800',
} as const

export function ResultView({ output }: { output: ResearchOutput | null }) {
  if (!output) return <div className="rounded bg-white p-4 text-sm text-slate-500">No result yet.</div>

  return (
    <div className="space-y-4 rounded border border-slate-200 bg-white p-4 text-sm">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>run {output.runId}</span>
        <span>
          {output.toolCallCount} tool calls · {output.elapsedSeconds.toFixed(1)}s · ${output.costUsd.toFixed(4)}
        </span>
      </div>

      <div>
        <div className="mb-2 flex items-center gap-2">
          <h3 className="text-base font-semibold">Summary</h3>
          <span className={clsx('rounded px-2 py-0.5 text-xs', CONF_COLOR[output.confidence])}>
            {output.confidence} confidence
          </span>
        </div>
        <p className="text-slate-800">{output.summary}</p>
      </div>

      {output.flags.length > 0 && (
        <div className="rounded bg-amber-50 p-3">
          <h4 className="mb-1 text-xs font-semibold uppercase text-amber-800">Flags for review</h4>
          <ul className="list-inside list-disc text-amber-900">
            {output.flags.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      <div>
        <h4 className="mb-2 text-sm font-semibold">Findings</h4>
        <ul className="space-y-3">
          {output.findings.map((f, i) => (
            <li key={i} className="rounded border border-slate-100 p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-slate-900">{f.claim}</p>
                <span className={clsx('shrink-0 rounded px-2 py-0.5 text-xs', CONF_COLOR[f.confidence])}>
                  {f.confidence}
                </span>
              </div>
              <p className="mt-1 text-slate-700">{f.evidence}</p>
              <p className="mt-2 text-xs text-slate-500">source: {f.sourceRef}</p>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold">Sources</h4>
        <ul className="space-y-1 text-xs">
          {output.sources.map((s) => (
            <li key={s.id}>
              <span className="font-mono text-slate-500">[{s.id}]</span>{' '}
              {s.url ? (
                <a className="text-forge-500 underline" href={s.url} target="_blank" rel="noreferrer">
                  {s.title}
                </a>
              ) : (
                <span>{s.title}</span>
              )}
              {s.dataVintage && <span className="ml-2 text-slate-400">({s.dataVintage})</span>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
