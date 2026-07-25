<script setup lang="ts">
import { computed } from 'vue'
import { AGENT_META_MAP } from '@/types'

const props = defineProps<{
  agentType: string
  content: string
  timestamp?: string
}>()

const meta = computed(() => {
  return AGENT_META_MAP[props.agentType] || AGENT_META_MAP.synthesis
})

const time = computed(() => {
  if (!props.timestamp) return ''
  try {
    const d = new Date(props.timestamp)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
})

const displayContent = computed(() => {
  if (props.content.length > 500) {
    return props.content.slice(0, 500) + '…'
  }
  return props.content
})
</script>

<template>
  <div class="agent-card" :class="meta.cssClass">
    <div class="flex items-center gap-2.5 mb-3">
      <div class="agent-avatar" :class="meta.cssClass">{{ meta.icon }}</div>
      <span class="font-semibold text-sm text-[var(--text)]">{{ meta.name }}</span>
      <span v-if="time" class="ml-auto text-xs text-[var(--text3)]">{{ time }}</span>
    </div>
    <div class="text-sm leading-relaxed text-[var(--text)] whitespace-pre-wrap">
      {{ displayContent }}
    </div>
  </div>
</template>
