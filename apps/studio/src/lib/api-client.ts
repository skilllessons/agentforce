import type { AttachmentRef, VerticalSummary } from './types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3000'

export async function listVerticals(): Promise<{ verticals: VerticalSummary[] }> {
  const res = await fetch(`${API}/v1/agents`, { cache: 'no-store' })
  if (!res.ok) return { verticals: [] }
  return res.json()
}

export async function startRun(args: {
  vertical: string
  query: string
  apiKey?: string
  attachments?: AttachmentRef[]
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
      output_format: 'json',
      max_seconds: args.maxSeconds,
      webhook_url: args.webhookUrl,
      attachments: args.attachments?.map((a) => ({
        fileId: a.fileId,
        kind: a.kind,
        filename: a.filename,
      })),
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
