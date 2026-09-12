<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listEncyclopedia, type CraftEntry } from '@/api/platform'
const entries = ref<CraftEntry[]>([])
const error = ref('')
onMounted(async () => { try { entries.value = await listEncyclopedia() } catch { error.value = '百科暂时不可用，请稍后重试。' } })
</script>
<template><main class="max-w-5xl mx-auto px-6 py-8"><h1 class="headline">技艺百科</h1><p class="body mb-6">已发布的非遗知识条目，附带可追溯来源。</p><p v-if="error" class="text-sm text-red-600">{{ error }}</p><p v-else-if="!entries.length" class="text-sm text-[var(--text-tertiary)]">暂未发布百科条目。</p><div v-else class="grid md:grid-cols-3 gap-4"><router-link v-for="entry in entries" :key="entry.slug" :to="`/encyclopedia/${entry.slug}`" class="setting-section no-underline"><h2 class="text-base">{{ entry.name }}</h2><p class="text-sm text-[var(--text-secondary)]">{{ entry.summary }}</p></router-link></div></main></template>
