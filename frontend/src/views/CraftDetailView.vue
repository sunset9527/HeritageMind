<script setup lang="ts">
import { onMounted, ref } from 'vue'; import { useRoute } from 'vue-router'; import { getCraft, type CraftEntry } from '@/api/platform'; import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
const route = useRoute(); const item = ref<CraftEntry | null>(null); const error = ref(''); onMounted(async()=>{ try { item.value=await getCraft(String(route.params.slug)) } catch { error.value='条目不存在或尚未发布。' } })
</script>
<template><main class="max-w-3xl mx-auto px-6 py-8"><p v-if="error">{{ error }}</p><article v-else-if="item"><EncyclopediaImage class="detail-image" :name="item.name" :image="item.image" /><h1 class="headline">{{ item.name }}</h1><p class="body mb-5">{{ item.summary }}</p><div class="whitespace-pre-wrap leading-8">{{ item.content }}</div></article></main></template>
<style scoped>.detail-image{height:300px;margin:0 0 28px}@media(max-width:640px){.detail-image{height:220px}}</style>
