import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import * as graphApi from '@/api/graph'
import type { GraphStats } from '@/types'

export const useGraphStore = defineStore('graph', () => {
  const stats = ref<GraphStats | null>(null)
  const graphHtml = ref<string | null>(null)
  const selectedLayout = ref('force')
  const selectedFilter = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStats() {
    try {
      stats.value = await graphApi.getStats()
    } catch (e: any) {
      error.value = e.message || '获取图谱统计失败'
    }
  }

  async function fetchVisualization() {
    isLoading.value = true
    error.value = null
    try {
      const resp = await graphApi.getVisualization(selectedFilter.value, selectedLayout.value)
      graphHtml.value = resp.html
    } catch (e: any) {
      error.value = e.message || '加载图谱失败'
    } finally {
      isLoading.value = false
    }
  }

  function setLayout(layout: string) {
    selectedLayout.value = layout
    fetchVisualization()
  }

  function setFilter(filter: string | null) {
    selectedFilter.value = filter
    fetchVisualization()
  }

  return {
    stats,
    graphHtml,
    selectedLayout,
    selectedFilter,
    isLoading,
    error,
    fetchStats,
    fetchVisualization,
    setLayout,
    setFilter,
  }
})
