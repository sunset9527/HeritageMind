<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'; import { useRoute } from 'vue-router'; import { getCraft, type CraftEntry } from '@/api/platform'; import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
const route = useRoute(); const item = ref<CraftEntry | null>(null); const error = ref(''); const loading = ref(true); let controller: AbortController | null = null
async function load(slug: string) { controller?.abort(); const request = new AbortController(); controller = request; loading.value = true; error.value = ''; item.value = null; try { item.value = await getCraft(slug, { signal: request.signal }) } catch { if (!request.signal.aborted) error.value = '条目不存在或尚未发布。' } finally { if (controller === request) { loading.value = false; controller = null } } }
watch(() => String(route.params.slug || ''), load, { immediate: true }); onBeforeUnmount(() => controller?.abort())
</script>
<template><main class="max-w-3xl mx-auto px-6 py-8"><p v-if="loading" role="status">正在加载条目…</p><p v-else-if="error">{{ error }} <button type="button" @click="load(String(route.params.slug || ''))">重新加载</button></p><article v-else-if="item"><EncyclopediaImage class="detail-image" :name="item.name" :image="item.image" /><h1 class="headline">{{ item.name }}</h1><div class="detail-copy whitespace-pre-wrap">{{ item.content }}</div></article></main></template>
<style scoped>.detail-image{height:300px;margin:0 0 28px}@media(max-width:640px){.detail-image{height:220px}}</style>
