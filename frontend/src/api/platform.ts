import client from './client'
import type { CraftItem } from '@/types'

export interface CraftEntry { name: string; slug: string; summary: string; content?: string }
export interface Source { name: string; url: string; evidence: string }
export interface Inheritor { name: string; slug: string; craft_name: string; region: string; recognition: string; biography: string; lineage: string; representative_works: string; sources: Source[] }
export interface DocumentSummary { total_documents: number }
export interface DashboardMetric { value: string; label: string; description: string }

export function buildDashboardMetrics(
  crafts?: CraftItem[],
  summary?: DocumentSummary,
): DashboardMetric[] {
  return [
    {
      value: crafts ? String(crafts.length) : '—',
      label: '已收录技艺',
      description: '来自服务端技艺目录',
    },
    {
      value: typeof summary?.total_documents === 'number' ? String(summary.total_documents) : '—',
      label: '已加载文档',
      description: '来自服务端文档摘要',
    },
    {
      value: '可核查',
      label: '知识质量',
      description: '资料治理与检索评测均留有记录',
    },
  ]
}

export async function listEncyclopedia() { return (await client.get<{ items: CraftEntry[] }>('/encyclopedia')).data.items }
export async function getCraft(slug: string) { return (await client.get<CraftEntry>(`/encyclopedia/${encodeURIComponent(slug)}`)).data }
export async function listInheritors() { return (await client.get<{ items: Inheritor[] }>('/inheritors')).data.items }
export async function getInheritor(slug: string) { return (await client.get<Inheritor>(`/inheritors/${encodeURIComponent(slug)}`)).data }
