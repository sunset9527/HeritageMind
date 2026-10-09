import client from './client'

export interface DashboardSummary {
  source_books: number
  document_count: number
  total_characters: number
  project_count: number
  inheritor_count: number
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await client.get<DashboardSummary>('/dashboard/summary')
  return data
}
