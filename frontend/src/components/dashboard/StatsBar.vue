<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCrafts, getDocumentSummary, type DocumentSummary } from '@/api/meta'
import { buildDashboardMetrics } from '@/api/platform'
import type { CraftItem } from '@/types'

const crafts = ref<CraftItem[]>()
const summary = ref<DocumentSummary>()
const metrics = computed(() => buildDashboardMetrics(crafts.value, summary.value))

onMounted(async () => {
  try { crafts.value = await getCrafts() } catch { /* Individual metrics keep their placeholder. */ }
  try { summary.value = await getDocumentSummary() } catch { /* Individual metrics keep their placeholder. */ }
})
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
.quality-band { display: grid; grid-template-columns: repeat(3, 1fr); max-width: 1120px; margin: 0 auto 70px; background: #173f47; color: #f8e8c8; }
.quality-metric { display: flex; align-items: center; gap: 16px; min-height: 100px; padding: 19px 32px; border-right: 1px solid rgba(246, 226, 178, .25); }
.quality-metric:last-child { border-right: 0; }
strong { color: #e6bd6b; font-family: var(--font-brush); font-size: 2.5rem; font-weight: 400; letter-spacing: .08em; white-space: nowrap; }
span, small { display: block; } span { font-size: .76rem; letter-spacing: .1em; } small { margin-top: 4px; color: #c8b797; font-size: .65rem; }
@media (max-width: 760px) { .quality-band { grid-template-columns: 1fr; margin-bottom: 44px; } .quality-metric { border-right: 0; border-bottom: 1px solid rgba(246, 226, 178, .25); } .quality-metric:last-child { border-bottom: 0; } }
</style>
