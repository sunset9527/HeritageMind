import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendQuery, streamQuery } from '@/api/query'
import type { ChatMessage, QueryResponse } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const currentProfile = ref('curious')
  const currentCraft = ref<string | null>(null)
  const includeNarrative = ref(false)
  const isSending = ref(false)
  const pendingQuestion = ref<string | null>(null)
  const streamSteps = ref<string[]>([])  // 当前流式进度

  function setProfile(profile: string) {
    currentProfile.value = profile
  }

  function setCraft(craft: string | null) {
    currentCraft.value = craft
  }

  function toggleNarrative() {
    includeNarrative.value = !includeNarrative.value
  }

  function setPendingQuestion(q: string) {
    pendingQuestion.value = q
  }

  function clearPendingQuestion() {
    pendingQuestion.value = null
  }

  async function sendQuestion(question: string) {
    const t0 = performance.now()
    isSending.value = true

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    }
    messages.value.push(userMsg)

    try {
      const resp: QueryResponse = await sendQuery({
        question,
        user_profile: currentProfile.value,
        include_narrative: includeNarrative.value,
        craft_filter: currentCraft.value,
      })

      const elapsedMs = Math.round(performance.now() - t0)

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: resp.answer,
        timestamp: new Date().toISOString(),
        metadata: {
          sourceAgents: resp.source_agents || [],
          debateSession: resp.debate_session,
          hasGaps: resp.has_gaps || false,
          gapReport: resp.gap_report || '',
          citations: resp.citations || [],
          elapsedMs,
          model: localStorage.getItem('hm_selected_model') || 'deepseek-chat',
        },
      }
      messages.value.push(assistantMsg)
      return assistantMsg
    } catch (e: any) {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `抱歉，请求失败：${e.message || '未知错误'}`,
        timestamp: new Date().toISOString(),
        metadata: { sourceAgents: [], hasGaps: false, gapReport: '', citations: [], elapsedMs: 0, model: '' },
      }
      messages.value.push(errorMsg)
      return errorMsg
    } finally {
      isSending.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    currentProfile,
    currentCraft,
    includeNarrative,
    isSending,
    pendingQuestion,
    streamSteps,
    setProfile,
    setCraft,
    toggleNarrative,
    setPendingQuestion,
    clearPendingQuestion,
    sendQuestion,
    clearMessages,
  }
})
