import client from './client'
import type { ChatHistoryListResponse, ChatDetailResponse } from '@/types'

export async function getHistory(limit = 20, offset = 0): Promise<ChatHistoryListResponse> {
  const { data } = await client.get<ChatHistoryListResponse>('/chat/history', {
    params: { limit, offset },
  })
  return data
}

export async function getChatDetail(chatId: number): Promise<ChatDetailResponse> {
  const { data } = await client.get<ChatDetailResponse>(`/chat/history/${chatId}`)
  return data
}
