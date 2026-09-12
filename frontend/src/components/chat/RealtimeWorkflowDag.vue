<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RealtimeWorkflow, WorkflowNodeStatus } from '@/types'

const props = defineProps<{ workflow: RealtimeWorkflow }>()
const expanded = ref(true)

const statusLabel: Record<WorkflowNodeStatus, string> = {
  pending: '等待', running: '执行中', completed: '完成', skipped: '跳过', fallback: '降级',
}
const statusMark: Record<WorkflowNodeStatus, string> = {
  pending: '○', running: '◌', completed: '✓', skipped: '–', fallback: '↳',
}
const regularNodes = computed(() => props.workflow.nodes.filter((node) => !node.id.startsWith('agent:')))
const agentNodes = computed(() => props.workflow.nodes.filter((node) => node.id.startsWith('agent:')))
</script>

<template>
  <section class="realtime-workflow">
    <button class="workflow-header" @click="expanded = !expanded">
      <span>⌘</span>
      <span>实时执行过程</span>
      <span v-if="!workflow.completed" class="live">● 运行中</span>
      <span class="collapse">{{ expanded ? '收起' : '展开' }}</span>
    </button>
    <div v-if="expanded" class="workflow-body">
      <div class="node-row">
        <template v-for="(node, index) in regularNodes" :key="node.id">
          <div class="node" :class="node.status" :title="statusLabel[node.status]">
            <span>{{ statusMark[node.status] }}</span>{{ node.label }}
          </div>
          <span v-if="index < regularNodes.length - 1" class="arrow">→</span>
        </template>
      </div>
      <div v-if="agentNodes.length" class="agent-lane">
        <span class="lane-title">本次专家</span>
        <div v-for="node in agentNodes" :key="node.id" class="node agent" :class="node.status">
          <span>{{ node.icon || '◌' }}</span>{{ node.label }} · {{ statusLabel[node.status] }}
        </div>
      </div>
      <div v-if="workflow.messages.length" class="message-lane">
        <div v-for="(message, index) in workflow.messages" :key="`${message.from_agent}-${index}`" class="message">
          <span class="message-kind">{{ { challenge: '质疑', response: '回应', supplement: '补充', agree: '认同' }[message.kind] }}</span>
          <span>{{ message.from_agent }} → {{ message.to_agent }}：{{ message.summary }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.realtime-workflow { margin: 10px 0 14px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 12px; background: rgba(249,247,244,.7); }
.workflow-header { width: 100%; display: flex; align-items: center; gap: 7px; border: 0; padding: 0; background: transparent; cursor: pointer; color: var(--text-secondary); font-size: 12px; text-align: left; }
.live { color: var(--accent); font-size: 11px; }.collapse { margin-left: auto; color: var(--text-tertiary); }
.workflow-body { margin-top: 10px; }.node-row { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; }
.node { padding: 4px 7px; border-radius: 7px; font-size: 11px; color: var(--text-secondary); background: var(--accent-soft); white-space: nowrap; }.arrow { color: var(--text-tertiary); }
.node.pending { background: #f0eee9; color: #97928a; }.node.running { background: #f8e3d7; color: #ad4b27; animation: pulse 1.2s infinite; }.node.completed { background: #e5f1e8; color: #3b7951; }.node.skipped { background: #f0eee9; color: #89847d; }.node.fallback { background: #fff1da; color: #9a6425; }
.agent-lane, .message-lane { margin-top: 9px; padding-top: 8px; border-top: 1px dashed var(--border); }.lane-title { margin-right: 6px; color: var(--text-tertiary); font-size: 11px; }.agent { display: inline-block; margin: 3px 4px 0 0; }
.message { display: flex; gap: 6px; margin-top: 5px; color: var(--text-secondary); font-size: 11px; line-height: 1.45; }.message-kind { flex: none; color: var(--accent); }
@keyframes pulse { 50% { opacity: .55; } }
</style>
