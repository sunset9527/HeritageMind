<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardSummary } from '@/api/dashboard'

const props = defineProps<{ summary?: DashboardSummary }>()
function formatTextAmount(characters?: number) {
  if (typeof characters !== 'number') return '—'
  const tenThousands = characters / 10000
  return `${tenThousands >= 10 ? Math.round(tenThousands) : tenThousands.toFixed(1).replace(/\.0$/, '')} 万字`
}
const metrics = computed(() => [
  { value: typeof props.summary?.project_count === 'number' ? String(props.summary.project_count) : '—', label: '已收录项目', description: '来自当前活动图书语料的项目元数据' },
  { value: typeof props.summary?.document_count === 'number' ? String(props.summary.document_count) : '—', label: '已加载知识片段', description: '图书逐页切分后可被检索的文本片段' },
  { value: formatTextAmount(props.summary?.total_characters), label: '可检索文本量', description: '当前活动图书语料中可供检索的正文总量' },
])
</script>

<template>
  <section class="quality-band" aria-label="平台知识概览">
    <div v-for="metric in metrics" :key="metric.label" class="quality-metric">
      <strong>{{ metric.value }}</strong>
      <div><span>{{ metric.label }}</span><small>{{ metric.description }}</small></div>
    </div>
  </section>
</template>

<style scoped>
.quality-band { display: grid; grid-template-columns: repeat(3, 1fr); max-width: 1120px; margin: 0 auto 70px; background: #293025; color: #f4f0e7; }
.quality-metric { display: flex; align-items: center; gap: 16px; min-height: 100px; padding: 19px 32px; border-right: 1px solid rgba(231, 222, 200, .22); }
.quality-metric:last-child { border-right: 0; }
strong { color: #d4b77e; font-family: var(--font-brush); font-size: 2.15rem; font-weight: 400; letter-spacing: .08em; white-space: nowrap; }
span, small { display: block; } span { font-size: .88rem; letter-spacing: .1em; } small { margin-top: 4px; color: #d8ded2; font-size: .78rem; }
@media (max-width: 760px) { .quality-band { grid-template-columns: 1fr; margin-bottom: 44px; } .quality-metric { border-right: 0; border-bottom: 1px solid rgba(246, 226, 178, .25); } .quality-metric:last-child { border-bottom: 0; } }
</style>
