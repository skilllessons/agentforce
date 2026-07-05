'use client'

import { ReactFlow, Background, Controls, type Edge, type Node } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

export function FlowDesigner({ vertical }: { vertical: string }) {
  const nodes: Node[] = [
    { id: 'trigger', position: { x: 0, y: 0 }, data: { label: 'Webhook trigger' }, type: 'input' },
    { id: 'agent', position: { x: 220, y: 0 }, data: { label: `${vertical} agent` } },
    { id: 'route', position: { x: 460, y: -60 }, data: { label: 'Route by confidence' } },
    { id: 'human', position: { x: 700, y: -100 }, data: { label: 'Human review queue' }, type: 'output' },
    { id: 'forward', position: { x: 700, y: -20 }, data: { label: 'Forward to CRM' }, type: 'output' },
  ]
  const edges: Edge[] = [
    { id: 't-a', source: 'trigger', target: 'agent' },
    { id: 'a-r', source: 'agent', target: 'route' },
    { id: 'r-h', source: 'route', target: 'human', label: 'flagged / low conf' },
    { id: 'r-f', source: 'route', target: 'forward', label: 'high conf' },
  ]

  return (
    <div className="h-[320px] rounded border border-slate-200 bg-white">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}
