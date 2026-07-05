'use client'

import { useCallback, useRef, useState } from 'react'
import clsx from 'clsx'
import { uploadFile } from '@/lib/api-client'
import type { AttachmentRef } from '@/lib/types'

const ACCEPT =
  'image/jpeg,image/png,image/gif,image/webp,application/pdf,audio/mpeg,audio/wav,audio/mp4,audio/webm,audio/ogg,text/plain,text/markdown,text/csv,application/json'
const MAX_FILES = 4

const KIND_LABEL: Record<AttachmentRef['kind'], string> = {
  image: 'IMG',
  pdf: 'PDF',
  audio: 'AUD',
  text: 'TXT',
}

export function AttachmentInput({
  apiKey,
  attachments,
  onChange,
}: {
  apiKey?: string
  attachments: AttachmentRef[]
  onChange: (next: AttachmentRef[]) => void
}) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return
      const slots = MAX_FILES - attachments.length
      if (slots <= 0) {
        setErr(`Max ${MAX_FILES} files`)
        return
      }
      setBusy(true)
      setErr(null)
      try {
        const picked = Array.from(files).slice(0, slots)
        const uploaded = await Promise.all(picked.map((f) => uploadFile(f, apiKey)))
        onChange([...attachments, ...uploaded])
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e))
      } finally {
        setBusy(false)
      }
    },
    [attachments, apiKey, onChange]
  )

  const remove = (fileId: string) => {
    onChange(attachments.filter((a) => a.fileId !== fileId))
  }

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">
        Attachments <span className="text-slate-400">(image, PDF, audio, text — up to {MAX_FILES})</span>
      </label>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          void handleFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          'cursor-pointer rounded border-2 border-dashed px-4 py-6 text-center text-sm',
          dragOver ? 'border-forge-500 bg-forge-50' : 'border-slate-300 bg-white',
          busy && 'opacity-50'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          className="hidden"
          onChange={(e) => void handleFiles(e.target.files)}
        />
        {busy ? 'Uploading…' : 'Drag files here or click to upload'}
      </div>
      {err && <p className="mt-1 text-xs text-rose-600">{err}</p>}
      {attachments.length > 0 && (
        <ul className="mt-2 space-y-1">
          {attachments.map((a) => (
            <li
              key={a.fileId}
              className="flex items-center justify-between rounded border border-slate-200 bg-white px-2 py-1 text-xs"
            >
              <div className="flex items-center gap-2">
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
                  {KIND_LABEL[a.kind]}
                </span>
                <span className="font-medium text-slate-800">{a.filename ?? a.fileId}</span>
                {a.size !== undefined && (
                  <span className="text-slate-400">{formatBytes(a.size)}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => remove(a.fileId)}
                className="text-slate-400 hover:text-rose-600"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}
