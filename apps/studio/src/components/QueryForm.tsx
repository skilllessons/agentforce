'use client'

import { useState } from 'react'
import { startRun, streamRun } from '@/lib/api-client'
import { AttachmentInput } from './AttachmentInput'
import type { AttachmentRef, ResearchOutput, StreamEvent } from '@/lib/types'

export function QueryForm({
  vertical,
  onStart,
  onEvent,
  onComplete,
  onError,
}: {
  vertical: string
  onStart: () => void
  onEvent: (e: StreamEvent) => void
  onComplete: (o: ResearchOutput) => void
  onError: (msg: string) => void
}) {
  const [query, setQuery] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [attachments, setAttachments] = useState<AttachmentRef[]>([])
  const [running, setRunning] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setRunning(true)
    onStart()
    try {
      const { run_id } = await startRun({
        vertical,
        query,
        apiKey: apiKey || undefined,
        attachments: attachments.length ? attachments : undefined,
      })
      const es = streamRun(run_id, apiKey || undefined)
      const eventTypes: StreamEvent['type'][] = [
        'run_start',
        'tool_start',
        'tool_result',
        'attachment_resolved',
        'attachment_skipped',
        'synthesis_start',
        'output',
        'stop',
        'error',
      ]
      for (const t of eventTypes) {
        es.addEventListener(t, (raw: MessageEvent<string>) => {
          const event = JSON.parse(raw.data) as StreamEvent
          onEvent(event)
          if (event.type === 'output') onComplete(event.output)
          if (event.type === 'error') onError(event.message)
        })
      }
      es.addEventListener('done', () => {
        es.close()
        setRunning(false)
      })
      es.addEventListener('error', () => {
        es.close()
        setRunning(false)
        onError('stream closed')
      })
    } catch (err) {
      setRunning(false)
      onError(String(err))
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">API key</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="af_<tenant>_<sig> (optional in dev)"
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Query</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={4}
          placeholder="e.g. Does a standard ISO CGL policy cover a data breach for a CA SaaS company?"
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
      </div>
      <AttachmentInput
        apiKey={apiKey || undefined}
        attachments={attachments}
        onChange={setAttachments}
      />
      <button
        type="submit"
        disabled={running}
        className="rounded bg-forge-500 px-4 py-2 text-sm font-medium text-white hover:bg-forge-600 disabled:opacity-50"
      >
        {running ? 'Running…' : 'Run agent'}
      </button>
    </form>
  )
}
