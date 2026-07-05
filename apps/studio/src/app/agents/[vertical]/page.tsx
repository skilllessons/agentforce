'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { QueryForm } from '@/components/QueryForm'
import { ResultView } from '@/components/ResultView'
import { FlowDesigner } from '@/components/FlowDesigner'
import type { ResearchOutput, StreamEvent } from '@/lib/types'

export default function VerticalPage() {
  const params = useParams<{ vertical: string }>()
  const vertical = params.vertical
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [output, setOutput] = useState<ResearchOutput | null>(null)
  const [running, setRunning] = useState(false)

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
      <section>
        <h2 className="mb-4 text-xl font-semibold capitalize">{vertical} agent</h2>
        <QueryForm
          vertical={vertical}
          onStart={() => {
            setEvents([])
            setOutput(null)
            setRunning(true)
          }}
          onEvent={(e) => setEvents((prev) => [...prev, e])}
          onComplete={(o) => {
            setOutput(o)
            setRunning(false)
          }}
          onError={() => setRunning(false)}
        />
        <h3 className="mt-8 mb-2 text-sm font-semibold text-slate-700">Live trace</h3>
        <ol className="space-y-1 text-sm">
          {events.map((e, i) => (
            <li key={i} className="font-mono text-xs text-slate-700">
              <span className="mr-2 inline-block w-40 text-forge-500">{e.type}</span>
              {'tool' in e
                ? e.tool
                : 'fileId' in e
                  ? `${e.fileId}${'kind' in e ? ` (${e.kind})` : ''}`
                  : ''}
            </li>
          ))}
          {running && events.length === 0 && (
            <li className="text-xs text-slate-400">Connecting…</li>
          )}
        </ol>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">Result</h2>
        <ResultView output={output} />
        <h3 className="mt-8 mb-2 text-sm font-semibold text-slate-700">Flow designer</h3>
        <FlowDesigner vertical={vertical} />
      </section>
    </div>
  )
}
