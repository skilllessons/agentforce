import type { AttachmentRef, ResearchOutput, VerticalSummary } from './types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function listVerticals(): Promise<{ verticals: VerticalSummary[] }> {
  // Isomorphic: server-side (home page) uses the absolute backend URL; client-side
  // (chat page) uses the same-origin proxy to avoid CORS.
  const url = typeof window === 'undefined' ? `${API}/v1/agents` : `/api/proxy/v1/agents`
  const res = await fetch(url, { cache: 'no-store' })
  if (!res.ok) return { verticals: [] }
  return res.json()
}

export async function startRun(args: {
  vertical: string
  query: string
  apiKey?: string
  threadId?: string
  images?: { media_type: string; data: string }[]
  maxSeconds?: number
  webhookUrl?: string
}): Promise<{ run_id: string; stream_url: string; estimated_seconds: number }> {
  const res = await fetch(`/api/proxy/v1/agents/${args.vertical}/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(args.apiKey ? { 'X-API-Key': args.apiKey } : {}),
    },
    body: JSON.stringify({
      query: args.query,
      thread_id: args.threadId,
      images: args.images?.length ? args.images : undefined,
      max_seconds: args.maxSeconds,
      webhook_url: args.webhookUrl,
    }),
  })
  if (!res.ok) throw new Error(`run start failed: ${res.status}`)
  return res.json()
}

export async function uploadFile(file: File, apiKey?: string): Promise<AttachmentRef> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/proxy/v1/files', {
    method: 'POST',
    headers: { ...(apiKey ? { 'X-API-Key': apiKey } : {}) },
    body: form,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`upload failed: ${res.status} ${detail}`)
  }
  const json = (await res.json()) as {
    file_id: string
    kind: 'image' | 'pdf' | 'audio' | 'text'
    content_type: string
    size: number
    filename?: string
  }
  return {
    fileId: json.file_id,
    kind: json.kind,
    contentType: json.content_type,
    size: json.size,
    filename: json.filename,
  }
}

export function streamRun(runId: string, apiKey?: string): EventSource {
  const url = new URL(`/api/proxy/v1/runs/${runId}/stream`, window.location.origin)
  if (apiKey) url.searchParams.set('api_key', apiKey)
  return new EventSource(url.toString(), { withCredentials: false })
}

export interface RunStatus {
  run_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  elapsed_seconds: number | null
  tool_calls: number
  cost_usd: number
  result: ResearchOutput | null
}

export interface RunEvent {
  kind: string
  payload: { _seq?: number; tool?: string; [k: string]: unknown }
}

export async function getRunEvents(runId: string): Promise<RunEvent[]> {
  const res = await fetch(`/api/proxy/v1/runs/${runId}/events`, { cache: 'no-store' })
  if (!res.ok) return []
  const evs: RunEvent[] = (await res.json()).events ?? []
  return evs.sort((a, b) => (a.payload._seq ?? 0) - (b.payload._seq ?? 0))
}

export async function getRun(runId: string, apiKey?: string): Promise<RunStatus> {
  const res = await fetch(`/api/proxy/v1/runs/${runId}`, {
    cache: 'no-store',
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
  })
  if (!res.ok) throw new Error(`get run failed: ${res.status}`)
  return res.json()
}

export interface RunSummary {
  id: string
  vertical: string
  query: string
  status: string
  cost_usd: number
  enqueued_at: string
}

export async function listRuns(apiKey?: string): Promise<RunSummary[]> {
  const res = await fetch(`/api/proxy/v1/runs`, {
    cache: 'no-store',
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
  })
  if (!res.ok) return []
  const data = await res.json()
  return data.runs ?? []
}

export interface SessionSummary {
  id: string
  vertical: string
  title: string | null
  updated_at: string
}

export async function createSession(vertical: string): Promise<string> {
  const res = await fetch(`/api/proxy/v1/agents/${vertical}/sessions`, { method: 'POST' })
  if (!res.ok) throw new Error(`create session failed: ${res.status}`)
  return (await res.json()).thread_id
}

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`/api/proxy/v1/sessions`, { cache: 'no-store' })
  if (!res.ok) return []
  return (await res.json()).sessions ?? []
}

export interface ThreadRun {
  id: string
  query: string
  status: string
  result: ResearchOutput | null
  cost_usd: number
  tool_call_count: number
  elapsed_seconds: number | null
}

export async function getSessionRuns(threadId: string): Promise<ThreadRun[]> {
  const res = await fetch(`/api/proxy/v1/sessions/${threadId}/runs`, { cache: 'no-store' })
  if (!res.ok) return []
  return (await res.json()).runs ?? []
}
