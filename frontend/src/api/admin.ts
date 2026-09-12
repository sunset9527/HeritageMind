import client from './client'
import type { AdminAgentConfiguration, AdminEvaluationRecord, AdminFeedbackRecord } from '@/types'

export async function getAdminAgents(): Promise<{ items: AdminAgentConfiguration[] }> {
  const { data } = await client.get('/admin/agents')
  return data
}

export async function updateAdminAgent(agentId: string, values: Omit<AdminAgentConfiguration, 'agent_id' | 'has_override'>) {
  const { data } = await client.patch(`/admin/agents/${agentId}`, values)
  return data
}

export async function getAdminEvaluations(limit = 100): Promise<{ items: AdminEvaluationRecord[] }> {
  const { data } = await client.get('/admin/evaluations', { params: { limit } })
  return data
}

export async function getAdminFeedback(limit = 100): Promise<{ items: AdminFeedbackRecord[] }> {
  const { data } = await client.get('/admin/feedback', { params: { limit } })
  return data
}
