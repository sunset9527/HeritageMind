<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'; import { useRoute } from 'vue-router'; import { getInheritor, type Inheritor } from '@/api/platform'
const route=useRoute(); const item=ref<Inheritor|null>(null); const error=ref(''); const loading=ref(true); let controller: AbortController | null = null
async function load(slug: string) { controller?.abort(); const request = new AbortController(); controller = request; loading.value = true; error.value = ''; item.value = null; try { item.value = await getInheritor(slug, { signal: request.signal }) } catch { if (!request.signal.aborted) error.value = '档案不存在或尚未发布。' } finally { if (controller === request) { loading.value = false; controller = null } } }
watch(() => String(route.params.slug || ''), load, { immediate: true }); onBeforeUnmount(() => controller?.abort())
</script>
<template><main class="max-w-3xl mx-auto px-6 py-8"><p v-if="loading" role="status">正在加载传承人档案…</p><p v-else-if="error">{{ error }} <button type="button" @click="load(String(route.params.slug || ''))">重新加载</button></p><article v-else-if="item"><h1 class="headline">{{ item.name }}</h1><p class="body">{{ item.craft_name }} · {{ item.region }}</p><p class="inheritor-copy mt-5 whitespace-pre-wrap">{{ item.biography }}</p></article></main></template>
