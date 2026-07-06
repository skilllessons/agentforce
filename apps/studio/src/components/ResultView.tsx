'use client'

import clsx from 'clsx'
import type { ResearchOutput } from '@/lib/types'

const CONF_COLOR = {
  high: 'bg-emerald-500/15 text-emerald-300',
  medium: 'bg-amber-500/15 text-amber-300',
  low: 'bg-rose-500/15 text-rose-300',
} as const

export function ResultView({ output }: { output: ResearchOutput | null }) {
  if (!output) return <div className="text-sm text-slate-500">No result yet.</div>

  return (
    <div className="space-y-5 text-sm">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-100">Summary</h3>
          <span className={clsx('rounded-full px-2 py-0.5 text-xs', CONF_COLOR[output.confidence])}>
            {output.confidence} confidence
          </span>
        </div>
        <p className="leading-relaxed text-slate-300">{output.summary}</p>
      </div>

      {output.flags.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
          <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-amber-300">
            Flags for review
          </h4>
          <ul className="list-inside list-disc space-y-1 text-amber-200/90">
            {output.flags.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Findings</h4>
        <ul className="space-y-3">
          {output.findings.map((f, i) => (
            <li key={i} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-slate-100">{f.claim}</p>
                <span className={clsx('shrink-0 rounded-full px-2 py-0.5 text-xs', CONF_COLOR[f.confidence])}>
                  {f.confidence}
                </span>
              </div>
              <p className="mt-1.5 leading-relaxed text-slate-400">{f.evidence}</p>
              <p className="mt-2 font-mono text-xs text-slate-600">{f.sourceRef}</p>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</h4>
        <ul className="space-y-2">
          {output.sources.map((s) =>
            s.url ? (
              <li key={s.id}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-center gap-2 rounded-lg border border-forge-500/30 bg-forge-500/10 px-3 py-2 text-sm text-forge-300 transition hover:border-forge-400 hover:bg-forge-500/20 hover:text-forge-200"
                >
                  <span className="font-mono text-xs text-forge-400/70">[{s.id}]</span>
                  <span className="flex-1 truncate font-medium">{s.title}</span>
                  {s.dataVintage && (
                    <span className="hidden shrink-0 text-xs text-slate-500 sm:inline">
                      {s.dataVintage}
                    </span>
                  )}
                  <svg
                    className="h-3.5 w-3.5 shrink-0 opacity-60 transition group-hover:opacity-100"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                  </svg>
                </a>
              </li>
            ) : (
              <li
                key={s.id}
                className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-sm text-slate-400"
              >
                <span className="font-mono text-xs text-slate-600">[{s.id}]</span>
                <span className="flex-1 truncate">{s.title}</span>
                {s.dataVintage && <span className="text-xs text-slate-600">{s.dataVintage}</span>}
              </li>
            )
          )}
        </ul>
      </div>
    </div>
  )
}
