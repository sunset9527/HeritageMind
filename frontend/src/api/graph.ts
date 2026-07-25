import client from './client'
import type { GraphStats, GraphVisualizeResponse, SubgraphResponse } from '@/types'

export async function getStats(): Promise<GraphStats> {
  const { data } = await client.get<GraphStats>('/graph/stats')
  return data
}

export async function getVisualization(
  filterType?: string | null,
  layout = 'force',
): Promise<GraphVisualizeResponse> {
  const params: Record<string, string> = { layout }
  if (filterType) params.filter_type = filterType
  const { data } = await client.get<GraphVisualizeResponse>('/graph/visualize', { params })
  return data
}

export async function getSubgraph(
  craftName: string,
  depth = 1,
): Promise<SubgraphResponse> {
  const { data } = await client.get<SubgraphResponse>(`/graph/subgraph/${craftName}`, {
    params: { depth },
  })
  return data
}
