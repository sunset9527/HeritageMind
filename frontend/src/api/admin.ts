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

export interface AdminCraft { id: number; name: string; slug: string; summary: string; content: string; status: string }
export interface AdminInheritor { id: number; name: string; craft_name: string; region: string; biography: string; status: string }
export interface GraphCandidate { id: number; source_entity: string; relation: string; target_entity: string; evidence_text: string; source_url: string; status: string }
export interface AuditLog { id: number; action: string; subject_type: string; subject_id: number; detail: string; created_at: string }

export async function getAdminCrafts(): Promise<{ items: AdminCraft[] }> { return (await client.get('/admin/crafts')).data }
export async function createAdminCraft(values: Pick<AdminCraft, 'name' | 'summary' | 'content'>): Promise<AdminCraft> { return (await client.post('/admin/crafts', values)).data }
export async function updateAdminCraft(id: number, values: Partial<Pick<AdminCraft, 'name' | 'summary' | 'content'>>): Promise<AdminCraft> { return (await client.patch(`/admin/crafts/${id}`, values)).data }
export async function publishAdminCraft(id: number): Promise<AdminCraft> { return (await client.post(`/admin/crafts/${id}/publish`)).data }
export async function deleteAdminCraft(id: number) { return (await client.delete(`/admin/crafts/${id}`)).data }

export async function getAdminInheritors(): Promise<{ items: AdminInheritor[] }> { return (await client.get('/admin/inheritors')).data }
export async function createAdminInheritor(values: Record<string, string>) { return (await client.post('/admin/inheritors', values)).data }
export async function updateAdminInheritor(id: number, values: Partial<AdminInheritor>) { return (await client.patch(`/admin/inheritors/${id}`, values)).data }
export async function publishAdminInheritor(id: number) { return (await client.post(`/admin/inheritors/${id}/publish`)).data }
export async function deleteAdminInheritor(id: number) { return (await client.delete(`/admin/inheritors/${id}`)).data }

export async function getGraphCandidates(): Promise<{ items: GraphCandidate[] }> { return (await client.get('/admin/graph-candidates')).data }
export async function scanGraphCandidates() { return (await client.post('/admin/graph-candidates/scan')).data as { scanned: number; created: number } }
export async function approveGraphCandidate(id: number) { return (await client.post(`/admin/graph-candidates/${id}/approve`)).data }
export async function rejectGraphCandidate(id: number, reason = '') { return (await client.post(`/admin/graph-candidates/${id}/reject`, { reason })).data }
export async function getAuditLogs(): Promise<{ items: AuditLog[] }> { return (await client.get('/admin/audit-logs')).data }
