<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { listInheritors, type Inheritor } from '@/api/platform'
const items = ref<Inheritor[]>([]); const error = ref(''); const loading = ref(true); let controller: AbortController | null = null
async function load() { controller?.abort(); const request = new AbortController(); controller = request; loading.value = true; error.value = ''; try { items.value = await listInheritors({ signal: request.signal }) } catch { if (!request.signal.aborted) error.value = '档案暂时不可用，请检查服务后重试。' } finally { if (controller === request) { loading.value = false; controller = null } } }
onMounted(load); onBeforeUnmount(() => controller?.abort())
</script>
<template><main class="heritage-page max-w-5xl mx-auto px-6 py-10"><p class="page-kicker">匠人档案</p><h1 class="page-title">传承人档案</h1><p class="page-intro">仅展示拥有公开来源证据的已发布档案。</p><p v-if="loading" class="text-sm text-[var(--text-tertiary)]" role="status">正在加载传承人档案…</p><p v-else-if="error" class="text-sm text-red-600">{{ error }} <button type="button" @click="load">重新加载</button></p><p v-else-if="!items.length" class="text-sm text-[var(--text-tertiary)]">暂未发布传承人档案。</p><div v-else class="grid md:grid-cols-3 gap-4"><router-link v-for="item in items" :key="item.slug" :to="`/inheritors/${item.slug}`" class="setting-section no-underline"><h2 class="text-base">{{ item.name }}</h2><p class="text-sm">{{ item.craft_name }} · {{ item.region }}</p></router-link></div></main></template>
