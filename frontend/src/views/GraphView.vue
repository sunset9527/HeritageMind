<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useGraphStore } from '@/stores/graph'

const graphStore = useGraphStore()

const layoutOptions = [
  { value: 'force', label: '力导向布局' },
  { value: 'circular', label: '圆形布局' },
]

const filterOptions = [
  { value: null, label: '全部类型' },
  { value: 'craft', label: '技艺' },
  { value: 'material', label: '材料' },
  { value: 'tool', label: '工具' },
  { value: 'inheritor', label: '传承人' },
  { value: 'region', label: '地域' },
  { value: 'dynasty', label: '朝代' },
]

const nodeColors: Record<string, string> = {
  craft: '#FF6B6B',
  material: '#4ECDC4',
  tool: '#45B7D1',
  inheritor: '#96CEB4',
  region: '#FFEAA7',
  dynasty: '#DDA0DD',
}

const nodeLabels: Record<string, string> = {
  craft: '技艺',
  material: '材料',
  tool: '工具',
  inheritor: '传承人',
  region: '地域',
  dynasty: '朝代',
}

const totalNodes = computed(() => graphStore.stats?.total_nodes ?? 0)
const totalEdges = computed(() => graphStore.stats?.total_edges ?? 0)
const nodeTypeCount = computed(() => Object.keys(graphStore.stats?.node_types ?? {}).length)

onMounted(async () => {
  await graphStore.fetchStats()
  await graphStore.fetchVisualization()
})
</script>

<template>
  <div class="heritage-page max-w-7xl mx-auto px-6 py-10">
    <p class="page-kicker">关系探索</p>
    <h1 class="page-title">知识图谱</h1>
    <p class="page-intro">
      非遗技艺 · 材料 · 工具 · 传承人 · 地域 · 朝代 多维关联
    </p>

    <!-- Stats -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="card graph-stat text-center">
        <div class="stat-num">{{ totalNodes }}</div>
        <div class="stat-label">节点总数</div>
      </div>
      <div class="card graph-stat text-center">
        <div class="stat-num">{{ totalEdges }}</div>
        <div class="stat-label">关系边数</div>
      </div>
      <div class="card graph-stat text-center">
        <div class="stat-num">{{ nodeTypeCount }} 种</div>
        <div class="stat-label">节点类型</div>
      </div>
    </div>

    <!-- Controls -->
    <div class="flex gap-4 mb-4">
      <div class="flex items-center gap-2">
        <label class="text-sm text-[var(--text2)]">布局</label>
        <select
          :value="graphStore.selectedLayout"
          @change="graphStore.setLayout(($event.target as HTMLSelectElement).value)"
          class="text-sm border border-[var(--border)] rounded-lg px-3 py-1.5 bg-white"
        >
          <option v-for="opt in layoutOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-[var(--text2)]">筛选</label>
        <select
          :value="graphStore.selectedFilter || ''"
          @change="graphStore.setFilter(($event.target as HTMLSelectElement).value || null)"
          class="text-sm border border-[var(--border)] rounded-lg px-3 py-1.5 bg-white"
        >
          <option v-for="opt in filterOptions" :key="opt.value ?? 'all'" :value="opt.value || ''">{{ opt.label }}</option>
        </select>
      </div>
    </div>

    <!-- Graph display -->
    <div class="card p-0 overflow-hidden">
      <div v-if="graphStore.isLoading" class="flex items-center justify-center h-[620px] text-[var(--text3)]">
        <span class="inline-block w-5 h-5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin mr-2"></span>
        加载知识图谱…
      </div>
      <div v-else-if="graphStore.error" class="flex items-center justify-center h-[620px] text-red-400 text-sm">
        {{ graphStore.error }}
      </div>
      <iframe
        v-else-if="graphStore.graphHtml"
        :srcdoc="graphStore.graphHtml"
        class="w-full border-0 overflow-hidden"
        style="height: 640px"
        sandbox="allow-scripts"
        title="知识图谱"
      />
      <div v-else class="flex items-center justify-center h-[620px] text-[var(--text3)] text-sm">
        暂无图谱数据
      </div>
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap gap-4 mt-4 justify-center">
      <div v-for="(color, type) in nodeColors" :key="type" class="flex items-center gap-2">
        <div class="w-4 h-4 rounded" :style="{ background: color }" />
        <span class="text-sm text-[var(--text2)]">{{ nodeLabels[type] }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graph-stat { background: #fffaf0; border-top: 3px solid var(--heritage); }.graph-stat:nth-child(2) { border-top-color: var(--history); }.graph-stat:nth-child(3) { border-top-color: var(--accent); }
</style>
