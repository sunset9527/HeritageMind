import client from './client'
import type { QueryRequest, QueryResponse } from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

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

/** SSE 流式查询 — 返回每一步进度 */
export function streamQuery(
  request: QueryRequest,
  onStep: (step: string, msg: string) => void,
  onDone: (answer: string, agents: any[], hasGaps: boolean, gapReport: string) => void,
  onError: (err: string) => void,
): AbortController {
  const controller = new AbortController()
  const token = localStorage.getItem('heritagemind_token') || ''

  fetch(`${API_BASE}/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
      'X-API-Key': localStorage.getItem('hm_user_api_key') || '',
      'X-Model': localStorage.getItem('hm_selected_model') || '',
      'X-API-Base': localStorage.getItem('hm_user_base_url') || '',
    },
    body: JSON.stringify(request),
    signal: controller.signal,
  }).then(async (resp) => {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }))
      onError(err.detail || '请求失败')
      return
    }
    const reader = resp.body?.getReader()
    if (!reader) { onError('无法读取响应流'); return }
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          try {
            const event = JSON.parse(data)
            if (event.step === 'done') {
              onDone(event.answer, event.source_agents || [], event.has_gaps || false, event.gap_report || '')
            } else if (event.step === 'error') {
              onError(event.msg)
            } else {
              onStep(event.step, event.msg)
            }
          } catch { /* skip parse errors */ }
        }
      }
    }
  }).catch((e) => {
    if (e.name !== 'AbortError') onError(e.message || '网络错误')
  })

  return controller
}

