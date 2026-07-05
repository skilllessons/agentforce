export type Confidence = 'high' | 'medium' | 'low'

export interface Finding {
  claim: string
  evidence: string
  sourceRef: string
  confidence: Confidence
}

export interface Source {
  id: string
  title: string
  url?: string | null
  retrievedAt: string
  dataVintage?: string | null
}

export interface ResearchOutput {
  summary: string
  findings: Finding[]
  sources: Source[]
  flags: string[]
  confidence: Confidence
  runId: string
  elapsedSeconds: number
  toolCallCount: number
  costUsd: number
}

export type StreamEvent =
  | { type: 'run_start'; runId: string; vertical: string; attachmentCount?: number }
  | { type: 'tool_start'; tool: string; input: unknown }
  | { type: 'tool_result'; tool: string; success: boolean; cached: boolean }
  | { type: 'attachment_resolved'; fileId: string; kind: string; bytes: number }
  | { type: 'attachment_skipped'; fileId: string; reason: string }
  | { type: 'synthesis_start' }
  | { type: 'output'; output: ResearchOutput }
  | { type: 'stop'; reason: string }
  | { type: 'error'; message: string }

export interface VerticalSummary {
  id: string
  tools: string[]
  avgRunSeconds: number | null
  avgCostUsd: number | null
}

export type AttachmentKind = 'image' | 'pdf' | 'audio' | 'text'

export interface AttachmentRef {
  fileId: string
  kind: AttachmentKind
  filename?: string
  contentType?: string
  size?: number
}
