<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listInheritors, type Inheritor } from '@/api/platform'
const items = ref<Inheritor[]>([]); const error = ref('')
onMounted(async () => { try { items.value = await listInheritors() } catch { error.value = '档案暂时不可用，请稍后重试。' } })
</script>
<template><main class="heritage-page max-w-5xl mx-auto px-6 py-10"><p class="page-kicker">匠人档案</p><h1 class="page-title">传承人档案</h1><p class="page-intro">仅展示拥有公开来源证据的已发布档案。</p><p v-if="error" class="text-sm text-red-600">{{ error }}</p><p v-else-if="!items.length" class="text-sm text-[var(--text-tertiary)]">暂未发布传承人档案。</p><div v-else class="grid md:grid-cols-3 gap-4"><router-link v-for="item in items" :key="item.slug" :to="`/inheritors/${item.slug}`" class="setting-section no-underline"><h2 class="text-base">{{ item.name }}</h2><p class="text-sm">{{ item.craft_name }} · {{ item.region }}</p></router-link></div></main></template>
