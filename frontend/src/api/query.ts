import client from './client'
import type { QueryRequest, QueryResponse } from '@/types'

export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  const { data } = await client.post<QueryResponse>('/query', request)
  return data
}

export async function sendQuerySimple(
  question: string,
  userProfile: string,
  includeNarrative: boolean,
): Promise<any> {
  const formData = new URLSearchParams()
  formData.append('question', question)
  formData.append('user_profile', userProfile)
  formData.append('include_narrative', String(includeNarrative))

  const { data } = await client.post('/query/simple', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}
