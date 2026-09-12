import type { RealtimeWorkflow, WorkflowNodeStatus, WorkflowSseEvent } from '@/types'

const eventStatus: Record<string, WorkflowNodeStatus> = {
  node_started: 'running',
  node_completed: 'completed',
  node_skipped: 'skipped',
  node_fallback: 'fallback',
}

export function reduceWorkflowEvent(
  current: RealtimeWorkflow | undefined,
  event: WorkflowSseEvent,
): RealtimeWorkflow | undefined {
  if (event.event === 'workflow_started') {
    return {
      runId: event.run_id || '',
      nodes: (event.nodes || []).map((node) => ({ ...node, status: 'pending' })),
      edges: event.edges || [],
      messages: [],
      completed: false,
    }
  }
  if (!current) return current

  if (event.event === 'workflow_graph_updated') {
    const known = new Set(current.nodes.map((node) => node.id))
    const nodes = [...current.nodes, ...(event.nodes || []).filter((node) => !known.has(node.id)).map((node) => ({ ...node, status: 'pending' as const }))]
    const edgeKeys = new Set(current.edges.map((edge) => `${edge.source}:${edge.target}`))
    const edges = [...current.edges, ...(event.edges || []).filter((edge) => !edgeKeys.has(`${edge.source}:${edge.target}`))]
    return { ...current, nodes, edges }
  }

  const status = event.event ? eventStatus[event.event] : undefined
  if (status) {
    const nodeId = event.step
    const nodes = current.nodes.map((node) => node.id === nodeId ? { ...node, status } : node)
    if (!nodes.some((node) => node.id === nodeId)) nodes.push({ id: nodeId, label: event.msg, status })
    return { ...current, nodes }
  }

  if (event.event === 'agent_message' && event.from_agent && event.to_agent && event.kind && event.summary) {
    return { ...current, messages: [...current.messages, { from_agent: event.from_agent, to_agent: event.to_agent, kind: event.kind, summary: event.summary }] }
  }
  if (event.event === 'done') return { ...current, completed: true }
  return current
}
