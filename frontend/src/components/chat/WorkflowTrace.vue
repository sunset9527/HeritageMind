<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Citation, WorkflowRoute, WorkflowTraceEntry } from '@/types'

const props = defineProps<{
  route: WorkflowRoute
  trace: WorkflowTraceEntry[]
  citations: Citation[]
}>()

const expanded = ref(false)
const routeLabel = computed(() => ({ rag: '文档检索', graph: '本地知识图谱', hybrid: '文档检索 + 本地知识图谱' }[props.route.execution_route]))
const statusIcon: Record<WorkflowTraceEntry['status'], string> = { completed: '✓', skipped: '–', fallback: '↳' }
const graphCitations = computed(() => props.citations.filter((item) => item.source === 'local_knowledge_graph'))
</script>

<template>
  <section class="mt-2 mb-3 rounded-xl border px-3 py-2.5" style="border-color: var(--border); background: rgba(249, 247, 244, 0.65)">
    <button class="w-full flex items-center gap-2 border-0 bg-transparent cursor-pointer text-left p-0" @click="expanded = !expanded">
      <span class="text-sm">🧭</span>
      <span class="text-xs font-medium" style="color: var(--text-secondary)">本次执行 · {{ routeLabel }}</span>
      <span class="ml-auto text-xs" style="color: var(--text-tertiary)">{{ expanded ? '收起' : '展开' }}</span>
    </button>
    <div class="flex flex-wrap items-center gap-1.5 mt-2">
      <span v-for="step in trace" :key="step.node" class="text-[11px] px-1.5 py-0.5 rounded" :style="{ background: step.status === 'fallback' ? '#FFF4E5' : 'var(--accent-soft)', color: step.status === 'fallback' ? '#9A6425' : 'var(--text-secondary)' }">
        {{ statusIcon[step.status] }} {{ step.node }}
      </span>
    </div>
    <div v-if="expanded" class="mt-3 space-y-2 text-xs" style="color: var(--text-secondary)">
      <p class="m-0">{{ route.reason }}</p>
      <p v-if="route.fallback_reason" class="m-0" style="color: #9A6425">降级：{{ route.fallback_reason }}</p>
      <div v-for="step in trace" :key="`${step.node}-${step.status}`" class="flex gap-2">
        <span class="font-medium">{{ statusIcon[step.status] }} {{ step.node }}</span>
        <span>{{ step.message }}<template v-if="step.elapsed_ms"> · {{ step.elapsed_ms }}ms</template></span>
      </div>
      <div v-if="graphCitations.length" class="pt-1">
        <div class="mb-1 font-medium">本地知识图谱证据</div>
        <div v-for="item in graphCitations" :key="item.title">{{ item.title }}</div>
      </div>
    </div>
  </section>
</template>
