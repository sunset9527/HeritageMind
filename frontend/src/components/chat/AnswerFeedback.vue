<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { submitFeedback } from '@/api/feedback'
import { useAuthStore } from '@/stores/auth'
import type { AnswerFeedback } from '@/types'

const props = defineProps<{ chatId?: number; feedback?: AnswerFeedback }>()
const emit = defineEmits<{ changed: [feedback: AnswerFeedback] }>()
const auth = useAuthStore()
const current = ref<AnswerFeedback | undefined>(props.feedback)
const comment = ref(props.feedback?.comment || '')
const saving = ref(false)
const canWrite = computed(() => auth.isAuthenticated && !!props.chatId && !saving.value)

async function choose(sentiment: 'up' | 'down') {
  if (!props.chatId || !canWrite.value) return
  saving.value = true
  try {
    const next = await submitFeedback(props.chatId, current.value?.sentiment === sentiment ? null : sentiment, comment.value)
    current.value = next
    emit('changed', next)
  } catch {
    ElMessage.error('反馈保存失败，请稍后重试')
  } finally { saving.value = false }
}

async function saveComment() {
  if (!props.chatId || current.value?.sentiment !== 'down') return
  saving.value = true
  try {
    const next = await submitFeedback(props.chatId, 'down', comment.value)
    current.value = next
    emit('changed', next)
  } catch { ElMessage.error('意见保存失败，请稍后重试') } finally { saving.value = false }
}
</script>

<template>
  <div v-if="auth.isAuthenticated && chatId" class="mb-4 text-[12px] text-[var(--text-tertiary)]">
    <span class="mr-2">这条回答有帮助吗？</span>
    <button class="feedback-btn" :class="{ selected: current?.sentiment === 'up' }" :disabled="!canWrite" @click="choose('up')">👍 有帮助</button>
    <button class="feedback-btn" :class="{ selected: current?.sentiment === 'down' }" :disabled="!canWrite" @click="choose('down')">👎 无帮助</button>
    <div v-if="current?.sentiment === 'down'" class="mt-2 flex gap-2 max-w-xl">
      <input v-model="comment" maxlength="500" placeholder="可选：告诉我们哪里需要改进" class="feedback-input" @keyup.enter="saveComment" />
      <button class="feedback-btn" :disabled="saving" @click="saveComment">保存</button>
    </div>
  </div>
</template>

<style scoped>
.feedback-btn { border: 1px solid var(--border); background: transparent; color: var(--text-secondary); border-radius: 999px; padding: 3px 8px; margin-right: 6px; cursor: pointer; }
.feedback-btn.selected { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.feedback-btn:disabled { opacity: .55; cursor: not-allowed; }
.feedback-input { flex: 1; border: 1px solid var(--border); border-radius: 8px; padding: 5px 8px; background: var(--surface); }
</style>
