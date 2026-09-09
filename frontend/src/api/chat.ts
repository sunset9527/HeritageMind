import client from './client'
import type {
  ChatHistoryListResponse, ChatDetailResponse, ChatSessionListResponse,
  ChatSessionMessagesResponse,
} from '@/types'

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

export async function getSessions(limit = 20): Promise<ChatSessionListResponse> {
  const { data } = await client.get<ChatSessionListResponse>('/chat/sessions', { params: { limit } })
  return data
}

export async function getSessionMessages(sessionId: string): Promise<ChatSessionMessagesResponse> {
  const { data } = await client.get<ChatSessionMessagesResponse>(`/chat/sessions/${sessionId}/messages`)
  return data
}
