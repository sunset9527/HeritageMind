<script setup lang="ts">
import { computed } from 'vue'
import type { DebateSession, SourceAgent } from '@/types'
import { AGENT_META_MAP } from '@/types'

const props = defineProps<{
  debateSession: DebateSession | null
  sourceAgents: SourceAgent[]
}>()

const agents = computed(() => {
  return props.sourceAgents.map(a => ({
    ...a,
    meta: AGENT_META_MAP[a.id] || AGENT_META_MAP.synthesis,
  }))
})
</script>

<template>
  <div>
    <!-- Tab-style header -->
    <div class="flex border-b border-[var(--border)] mb-3">
      <button class="px-3 py-2 text-sm font-semibold text-[var(--text)] border-b-2 border-[var(--text)]">⚔️ 辩论</button>
      <button class="px-3 py-2 text-sm text-[var(--text3)]">📚 引用</button>
    </div>

    <!-- Debate rounds -->
    <div v-if="debateSession?.rounds?.length" class="timeline">
      <div
        v-for="round in debateSession.rounds"
        :key="round.round_num"
        class="timeline-node"
      >
        <div class="flex items-center gap-2 mb-1 font-semibold text-sm">
          <span>{{ AGENT_META_MAP[round.agent_name]?.icon || '💬' }}</span>
          <span>{{ AGENT_META_MAP[round.agent_name]?.name || '专家' }}</span>
        </div>
        <div class="text-sm text-[var(--text2)]">
          {{ round.content.slice(0, 150) }}{{ round.content.length > 150 ? '…' : '' }}
        </div>
      </div>
    </div>

    <!-- Fallback: show agent contributions if no debate rounds -->
    <div v-else>
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="py-2 border-b border-[var(--border)] last:border-0"
      >
        <div class="flex items-center gap-2 mb-1 text-sm font-medium">
          <span>{{ agent.meta.icon }}</span>
          <span>{{ agent.meta.name }}</span>
        </div>
        <div class="text-xs text-[var(--text2)]">{{ agent.contribution }}</div>
      </div>
    </div>
  </div>
</template>
