import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamQuery } from '@/api/query'
import { getSessionMessages } from '@/api/chat'
import type { ChatMessage } from '@/types'
import { reduceWorkflowEvent } from '@/utils/workflowRuntime'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const currentProfile = ref('curious')
  const currentCraft = ref<string | null>(null)
  const includeNarrative = ref(false)
  const isSending = ref(false)
  const pendingQuestion = ref<string | null>(null)
  const streamSteps = ref<string[]>([])  // 当前流式进度
  const activeSessionId = ref<string | null>(null)

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
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '正在分析…',
      timestamp: new Date().toISOString(),
      metadata: { sourceAgents: [], hasGaps: false, gapReport: '', citations: [], elapsedMs: 0, model: localStorage.getItem('hm_selected_model') || 'deepseek-chat' },
    }
    messages.value.push(assistantMsg)

    try {
      return await new Promise<ChatMessage>((resolve) => {
        streamQuery(
          {
            question,
            user_profile: currentProfile.value,
            include_narrative: includeNarrative.value,
            craft_filter: currentCraft.value,
            session_id: activeSessionId.value,
          },
          (event) => {
            streamSteps.value.push(event.msg)
            assistantMsg.metadata!.realtimeWorkflow = reduceWorkflowEvent(assistantMsg.metadata!.realtimeWorkflow, event)
          },
          (event) => {
            const elapsedMs = Math.round(performance.now() - t0)
            assistantMsg.content = event.answer || '抱歉，未收到回答内容。'
            assistantMsg.metadata!.sourceAgents = event.source_agents || []
            assistantMsg.metadata!.hasGaps = event.has_gaps || false
            assistantMsg.metadata!.gapReport = event.gap_report || ''
            assistantMsg.metadata!.citations = event.citations || []
            assistantMsg.metadata!.workflowTrace = event.workflow_trace || []
            assistantMsg.metadata!.elapsedMs = elapsedMs
            assistantMsg.metadata!.realtimeWorkflow = reduceWorkflowEvent(assistantMsg.metadata!.realtimeWorkflow, event)
            if (typeof event.session_id === 'string') {
              activeSessionId.value = event.session_id
              assistantMsg.metadata!.sessionId = event.session_id
            }
            isSending.value = false
            resolve(assistantMsg)
          },
          (err) => {
            assistantMsg.content = `抱歉，请求失败：${err || '未知错误'}`
            assistantMsg.metadata!.elapsedMs = Math.round(performance.now() - t0)
            isSending.value = false
            resolve(assistantMsg)
          },
        )
      })
    } finally {
      isSending.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  function startNewSession() {
    activeSessionId.value = null
    messages.value = []
  }

  async function loadSession(sessionId: string) {
    const response = await getSessionMessages(sessionId)
    activeSessionId.value = sessionId
    messages.value = response.items.flatMap((turn) => [
      { id: `u-${turn.id}`, role: 'user' as const, content: turn.question, timestamp: turn.created_at },
      {
        id: `a-${turn.id}`,
        role: 'assistant' as const,
        content: turn.answer,
        timestamp: turn.created_at,
        metadata: { sourceAgents: [], hasGaps: turn.has_gaps, gapReport: '', citations: [], elapsedMs: 0, model: '' },
      },
    ])
  }

  return {
    messages,
    currentProfile,
    currentCraft,
    includeNarrative,
    isSending,
    pendingQuestion,
    streamSteps,
    activeSessionId,
    setProfile,
    setCraft,
    toggleNarrative,
    setPendingQuestion,
    clearPendingQuestion,
    sendQuestion,
    clearMessages,
    startNewSession,
    loadSession,
  }
})
