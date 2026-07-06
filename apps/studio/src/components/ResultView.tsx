'use client'

import { ExternalLink } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { ResearchOutput } from '@/lib/types'

export function ResultView({ output }: { output: ResearchOutput | null }) {
  if (!output) return <div className="text-sm text-muted-foreground">No result yet.</div>

  return (
    <div className="space-y-5 text-sm">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <h3 className="text-base font-semibold text-foreground">Summary</h3>
          <Badge variant={output.confidence}>{output.confidence} confidence</Badge>
        </div>
        <p className="leading-relaxed text-foreground/80">{output.summary}</p>
      </div>

      {output.flags.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Flags for review
          </h4>
          <ul className="list-inside list-disc space-y-1 text-amber-900/90">
            {output.flags.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Findings
        </h4>
        <ul className="space-y-3">
          {output.findings.map((f, i) => (
            <li key={i} className="rounded-xl border border-border bg-background/40 p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-foreground">{f.claim}</p>
                <Badge variant={f.confidence}>{f.confidence}</Badge>
              </div>
              <p className="mt-1.5 leading-relaxed text-muted-foreground">{f.evidence}</p>
              <p className="mt-2 font-mono text-xs text-muted-foreground/60">{f.sourceRef}</p>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Sources
        </h4>
        <ul className="space-y-2">
          {output.sources.map((s) =>
            s.url ? (
              <li key={s.id}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary transition-colors hover:border-primary hover:bg-primary/20"
                >
                  <span className="font-mono text-xs text-primary/60">[{s.id}]</span>
                  <span className="flex-1 truncate font-medium">{s.title}</span>
                  {s.dataVintage && (
                    <span className="hidden shrink-0 text-xs text-muted-foreground sm:inline">
                      {s.dataVintage}
                    </span>
                  )}
                  <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-60 transition-opacity group-hover:opacity-100" />
                </a>
              </li>
            ) : (
              <li
                key={s.id}
                className="flex items-center gap-2 rounded-lg border border-border bg-background/40 px-3 py-2 text-sm text-muted-foreground"
              >
                <span className="font-mono text-xs text-muted-foreground/60">[{s.id}]</span>
                <span className="flex-1 truncate">{s.title}</span>
                {s.dataVintage && <span className="text-xs text-muted-foreground/60">{s.dataVintage}</span>}
              </li>
            ),
          )}
        </ul>
      </div>
    </div>
  )
}
