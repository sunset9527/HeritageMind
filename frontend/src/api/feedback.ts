import client from './client'
import type { AnswerFeedback } from '@/types'

export async function submitFeedback(chatId: number, sentiment: 'up' | 'down' | null, comment?: string): Promise<AnswerFeedback> {
  const { data } = await client.post<AnswerFeedback>('/feedback', {
    chat_id: chatId,
    sentiment,
    comment: comment || null,
  })
  return data
}
