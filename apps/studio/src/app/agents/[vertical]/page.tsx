'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { ResultView } from '@/components/ResultView'
import {
  startRun,
  getRun,
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

// Query templates (prompt presets) — click to pre-fill, then fill the {blanks}.
const TEMPLATES = [
  { label: 'Coverage check', text: 'Does ISO form {form} cover {peril} for a {state} {business}?' },
  { label: 'Model law', text: 'What does NAIC {MDL-NNN} say about {topic}?' },
  { label: 'Form lookup', text: 'What does ISO form {form} say about {topic}?' },
  { label: 'Surplus lines', text: "What are {state}'s surplus lines requirements for {line}?" },
  { label: 'Carrier lookup', text: 'What is the NAIC company code and group for {carrier}?' },
]

interface Message {
  runId: string
  query: string
  status: string
  output: ResearchOutput | null
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
  const threadRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Click a template → fill the input and select the first {blank} to type over.
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

  const newChat = () => {
    setThreadId(null)
    setMessages([])
    setInput('')
  }

  const submit = async () => {
    const q = input.trim()
    if (!q || busy) return
    // Guard: don't spend a run on an unfilled template placeholder.
    if (/\{[^}]+\}/.test(q)) {
      setHint('Fill in the {…} placeholders before sending.')
      return
    }
    setHint('')
    setBusy(true)
    setInput('')
    try {
      // Lazily open a thread on the first message of a conversation.
      let tid = threadId
      if (!tid) {
        tid = await createSession(vertical)
        setThreadId(tid)
      }
      const { run_id } = await startRun({ vertical, query: q, threadId: tid })
      setMessages((prev) => [...prev, { runId: run_id, query: q, status: 'queued', output: null }])
      for (let i = 0; i < 80; i++) {
        const run = await getRun(run_id)
        setLast({ status: run.status })
        if (run.status === 'completed' && run.result) {
          setLast({
            output: run.result,
            meta: { tools: run.tool_calls, cost: run.cost_usd, elapsed: run.elapsed_seconds },
          })
          break
        }
        if (run.status === 'failed') break
        await new Promise((r) => setTimeout(r, 1500))
      }
    } catch {
      setLast({ status: 'failed' })
    } finally {
      setBusy(false)
      refreshSessions()
    }
  }

  // Open a past conversation → replay its runs into the thread.
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
      {/* ── LEFT SIDEBAR ─────────────────────────────── */}
      <aside className="flex w-72 flex-col gap-6 overflow-y-auto border-r border-white/10 bg-[#171717] p-4">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0d] px-2 py-1.5 text-sm text-slate-200"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Connectors
          </div>
          <ul className="space-y-1">
            {connectors.map((c) => (
              <li key={c} className="flex items-center gap-2 text-sm text-slate-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {c}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex-1">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Conversations
            </span>
            <button onClick={newChat} className="text-xs text-forge-400 hover:text-forge-300">
              + New
            </button>
          </div>
          <ul className="space-y-1">
            {sessions.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => openSession(s.id)}
                  className={`w-full truncate rounded-lg px-2 py-1.5 text-left text-sm hover:bg-white/5 ${
                    s.id === threadId ? 'bg-white/10 text-white' : 'text-slate-300'
                  }`}
                  title={s.title ?? undefined}
                >
                  {s.title ?? 'New conversation'}
                </button>
              </li>
            ))}
            {sessions.length === 0 && <li className="text-xs text-slate-500">No conversations yet</li>}
          </ul>
        </div>
      </aside>

      {/* ── MAIN CHAT ────────────────────────────────── */}
      <main className="flex flex-1 flex-col bg-[#0d0d0d]">
        <div ref={threadRef} className="flex-1 space-y-6 overflow-y-auto px-6 py-8">
          {messages.length === 0 && (
            <div className="mx-auto mt-24 max-w-xl text-center text-slate-500">
              <div className="text-lg font-medium capitalize text-slate-200">{vertical} agent</div>
              <div className="mt-2 text-sm">
                Ask a question — follow-ups keep the conversation context.
              </div>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {TEMPLATES.map((t) => (
                  <button
                    key={t.label}
                    onClick={() => pickTemplate(t.text)}
                    className="rounded-full border border-white/10 bg-[#171717] px-3 py-1.5 text-xs text-slate-300 transition hover:border-forge-500 hover:text-white"
                    title={t.text}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className="mx-auto max-w-3xl space-y-4">
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl bg-forge-500 px-4 py-2 text-sm text-white">
                  {m.query}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-[#171717] p-4">
                {!m.output ? (
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    {(m.status === 'queued' || m.status === 'running') && (
                      <span className="h-2 w-2 animate-pulse rounded-full bg-forge-500" />
                    )}
                    {STATUS_LABEL[m.status] ?? m.status}
                  </div>
                ) : (
                  <>
                    {m.meta && (
                      <div className="mb-3 text-xs text-slate-500">
                        {m.meta.tools} tool calls · {m.meta.elapsed?.toFixed(1)}s · $
                        {m.meta.cost.toFixed(4)}
                      </div>
                    )}
                    <ResultView output={m.output} />
                  </>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 pb-6 pt-2">
          {hint && (
            <div className="mx-auto mb-2 max-w-3xl text-center text-xs text-amber-400">{hint}</div>
          )}
          <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-white/10 bg-[#171717] p-2 shadow-lg">
            <textarea
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
              placeholder="Ask the insurance agent…"
              className="flex-1 resize-none bg-transparent px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
            />
            <button
              onClick={submit}
              disabled={busy || !input.trim()}
              className="rounded-xl bg-forge-500 px-5 py-3 text-sm font-medium text-white hover:bg-forge-600 disabled:opacity-40"
            >
              {busy ? '…' : 'Send'}
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
