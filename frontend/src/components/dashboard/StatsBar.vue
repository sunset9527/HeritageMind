<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useGraphStore } from '@/stores/graph'

const graphStore = useGraphStore()

const nodes = computed(() => graphStore.stats?.total_nodes ?? 47)
const edges = computed(() => graphStore.stats?.total_edges ?? 52)

onMounted(() => { graphStore.fetchStats() })
</script>

<template>
  <section class="max-w-5xl mx-auto px-6 mb-20">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
      <div>
        <div class="stat-num">{{ nodes }}</div>
        <div class="stat-label">知识节点</div>
      </div>
      <div>
        <div class="stat-num">{{ edges }}</div>
        <div class="stat-label">语义关联</div>
      </div>
      <div>
        <div class="stat-num">6<span style="font-size: 1.2rem; font-weight: 400; color: var(--text-tertiary)"> 种</span></div>
        <div class="stat-label">非遗技艺</div>
      </div>
      <div>
        <div class="stat-num">3<span style="font-size: 1.2rem; font-weight: 400; color: var(--text-tertiary)"> 位</span></div>
        <div class="stat-label">专家 Agent</div>
      </div>
    </div>
  </section>
</template>
