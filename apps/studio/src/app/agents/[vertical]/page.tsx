'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { Paperclip, ArrowUp, Plus, Loader2, X } from 'lucide-react'
import { ResultView } from '@/components/ResultView'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  startRun,
  getRun,
  getRunEvents,
  listVerticals,
  createSession,
  listSessions,
  getSessionRuns,
  type SessionSummary,
} from '@/lib/api-client'
import type { ResearchOutput } from '@/lib/types'

const MODELS = [
  { id: 'claude-opus-4-7', label: 'Claude Opus 4.7' },
  { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
  { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
]

const STATUS_LABEL: Record<string, string> = {
  queued: 'Queued…',
  running: 'Thinking — calling tools and Claude…',
  completed: 'Completed',
  failed: 'Failed',
}

const TEMPLATES = [
  { label: 'Coverage check', text: 'Does ISO form {form} cover {peril} for a {state} {business}?' },
  { label: 'Model law', text: 'What does NAIC {MDL-NNN} say about {topic}?' },
  { label: 'Form lookup', text: 'What does ISO form {form} say about {topic}?' },
  { label: 'Surplus lines', text: "What are {state}'s surplus lines requirements for {line}?" },
  { label: 'Carrier lookup', text: 'What is the NAIC company code and group for {carrier}?' },
]

const TRACE_LABEL = (kind: string, tool?: string): string | null => {
  switch (kind) {
    case 'run_start':
      return 'Started'
    case 'tool_start':
      return `Calling ${tool}`
    case 'tool_result':
      return `✓ ${tool}`
    case 'synthesis_start':
      return 'Synthesizing answer…'
    default:
      return null
  }
}

interface Message {
  runId: string
  query: string
  status: string
  output: ResearchOutput | null
  trace?: string[]
  meta?: { tools: number; cost: number; elapsed: number | null }
}

export default function VerticalPage() {
  const { vertical } = useParams<{ vertical: string }>()
  const [messages, setMessages] = useState<Message[]>([])
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [threadId, setThreadId] = useState<string | null>(null)
  const [connectors, setConnectors] = useState<string[]>([])
  const [model, setModel] = useState(MODELS[0].id)
  const [input, setInput] = useState('')
  const [hint, setHint] = useState('')
  const [busy, setBusy] = useState(false)
  const [images, setImages] = useState<{ media_type: string; data: string; name: string }[]>([])
  const threadRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listVerticals().then(({ verticals }) => {
      const v = verticals.find((x) => x.id === vertical)
      if (v) setConnectors(v.tools)
    })
    refreshSessions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vertical])

  const refreshSessions = () => listSessions().then(setSessions)

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const setLast = (patch: Partial<Message>) =>
    setMessages((prev) => prev.map((m, i) => (i === prev.length - 1 ? { ...m, ...patch } : m)))

  const pickTemplate = (text: string) => {
    setInput(text)
    setHint('')
    setTimeout(() => {
      const el = inputRef.current
      if (!el) return
      el.focus()
      const m = text.match(/\{[^}]+\}/)
      if (m) el.setSelectionRange(m.index!, m.index! + m[0].length)
    }, 0)
  }

  const onFiles = (files: FileList | null) => {
    if (!files) return
    Array.from(files).slice(0, 4).forEach((f) => {
      const reader = new FileReader()
      reader.onload = () => {
        const data = (reader.result as string).split(',')[1]
        setImages((prev) => [...prev, { media_type: f.type, data, name: f.name }])
      }
      reader.readAsDataURL(f)
    })
  }

  const newChat = () => {
    setThreadId(null)
    setMessages([])
    setInput('')
  }

  const submit = async () => {
    const q = input.trim()
    if (!q || busy) return
    if (/\{[^}]+\}/.test(q)) {
      setHint('Fill in the {…} placeholders before sending.')
      return
    }
    setHint('')
    setBusy(true)
    setInput('')
    try {
      let tid = threadId
      if (!tid) {
        tid = await createSession(vertical)
        setThreadId(tid)
      }
      const imgs = images.map((i) => ({ media_type: i.media_type, data: i.data }))
      const { run_id } = await startRun({ vertical, query: q, threadId: tid, images: imgs })
      setImages([])
      setMessages((prev) => [...prev, { runId: run_id, query: q, status: 'queued', output: null }])
      for (let i = 0; i < 120; i++) {
        const [run, events] = await Promise.all([getRun(run_id), getRunEvents(run_id)])
        const trace = events
          .map((e) => TRACE_LABEL(e.kind, e.payload.tool as string | undefined))
          .filter((x): x is string => x !== null)
        setLast({ status: run.status, trace })
        if (run.status === 'completed' && run.result) {
          setLast({
            output: run.result,
            meta: { tools: run.tool_calls, cost: run.cost_usd, elapsed: run.elapsed_seconds },
          })
          break
        }
        if (run.status === 'failed') break
        await new Promise((r) => setTimeout(r, 1000))
      }
    } catch {
      setLast({ status: 'failed' })
    } finally {
      setBusy(false)
      refreshSessions()
    }
  }

  const openSession = async (id: string) => {
    setThreadId(id)
    const runs = await getSessionRuns(id)
    setMessages(
      runs.map((r) => ({
        runId: r.id,
        query: r.query,
        status: r.status,
        output: r.result,
        meta: { tools: r.tool_call_count, cost: r.cost_usd, elapsed: r.elapsed_seconds },
      })),
    )
  }

  return (
    <div className="flex h-full">
      {/* ── SIDEBAR ── */}
      <aside className="flex w-64 flex-col gap-6 overflow-y-auto border-r border-border bg-card p-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="h-9 w-full rounded-lg border border-border bg-background px-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Connectors
          </div>
          <ul className="space-y-1.5">
            {connectors.map((c) => (
              <li key={c} className="flex items-center gap-2 text-sm text-foreground/80">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {c}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex-1">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Conversations
            </span>
            <Button variant="ghost" size="sm" onClick={newChat} className="h-7 gap-1 px-2">
              <Plus className="h-3.5 w-3.5" /> New
            </Button>
          </div>
          <ul className="space-y-0.5">
            {sessions.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => openSession(s.id)}
                  className={cnActive(s.id === threadId)}
                  title={s.title ?? undefined}
                >
                  {s.title ?? 'New conversation'}
                </button>
              </li>
            ))}
            {sessions.length === 0 && (
              <li className="px-2 text-xs text-muted-foreground">No conversations yet</li>
            )}
          </ul>
        </div>
      </aside>

      {/* ── CHAT ── */}
      <main className="flex flex-1 flex-col bg-background">
        <div ref={threadRef} className="flex-1 space-y-6 overflow-y-auto px-6 py-8">
          {messages.length === 0 && (
            <div className="mx-auto mt-28 max-w-xl text-center">
              <h2 className="font-serif text-3xl font-medium capitalize tracking-tight">
                {vertical} agent
              </h2>
              <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
                Ask a question — follow-ups keep the conversation context.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {TEMPLATES.map((t) => (
                  <button
                    key={t.label}
                    onClick={() => pickTemplate(t.text)}
                    className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-foreground/80 transition-colors hover:border-primary hover:text-foreground"
                    title={t.text}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className="mx-auto max-w-3xl space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                  {m.query}
                </div>
              </div>
              <Card>
                <CardContent>
                  {!m.output ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        {(m.status === 'queued' || m.status === 'running') && (
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                        )}
                        {STATUS_LABEL[m.status] ?? m.status}
                      </div>
                      {m.trace && m.trace.length > 0 && (
                        <ul className="space-y-1 border-l border-border pl-3 text-xs text-muted-foreground">
                          {m.trace.map((t, j) => (
                            <li key={j}>{t}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ) : (
                    <>
                      {m.meta && (
                        <div className="mb-3 text-xs text-muted-foreground">
                          {m.meta.tools} tool calls · {m.meta.elapsed?.toFixed(1)}s · $
                          {m.meta.cost.toFixed(4)}
                        </div>
                      )}
                      <ResultView output={m.output} />
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          ))}
        </div>

        {/* input */}
        <div className="px-6 pb-6 pt-2">
          {hint && (
            <div className="mx-auto mb-2 max-w-3xl text-center text-xs text-amber-400">{hint}</div>
          )}
          {images.length > 0 && (
            <div className="mx-auto mb-2 flex max-w-3xl flex-wrap gap-2">
              {images.map((img, i) => (
                <span
                  key={i}
                  className="flex items-center gap-1 rounded-lg border border-border bg-card px-2 py-1 text-xs text-foreground/80"
                >
                  🖼 {img.name}
                  <button
                    onClick={() => setImages((prev) => prev.filter((_, j) => j !== i))}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-lg">
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(e) => onFiles(e.target.files)}
            />
            <Button variant="ghost" size="icon" onClick={() => fileRef.current?.click()} title="Attach image">
              <Paperclip className="h-4 w-4" />
            </Button>
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  submit()
                }
              }}
              rows={1}
              placeholder={`Ask the ${vertical} agent…`}
              className="max-h-40 min-h-[2.5rem] py-2.5"
            />
            <Button size="icon" onClick={submit} disabled={busy || !input.trim()} title="Send">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}

function cnActive(active: boolean): string {
  return `w-full truncate rounded-lg px-2 py-2 text-left text-sm transition-colors ${
    active ? 'bg-accent text-foreground' : 'text-foreground/70 hover:bg-accent/50'
  }`
}
