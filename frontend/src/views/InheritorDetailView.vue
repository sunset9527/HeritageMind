<script setup lang="ts">
import { onMounted, ref } from 'vue'; import { useRoute } from 'vue-router'; import { getInheritor, type Inheritor } from '@/api/platform'
const route=useRoute(); const item=ref<Inheritor|null>(null); const error=ref(''); onMounted(async()=>{try{item.value=await getInheritor(String(route.params.slug))}catch{error.value='档案不存在或尚未发布。'}})
</script>
<template><main class="max-w-3xl mx-auto px-6 py-8"><p v-if="error">{{ error }}</p><article v-else-if="item"><h1 class="headline">{{ item.name }}</h1><p class="body">{{ item.craft_name }} · {{ item.region }}</p><p class="mt-5 whitespace-pre-wrap">{{ item.biography }}</p><section class="setting-section mt-6"><h2>公开来源</h2><ul><li v-for="source in item.sources" :key="source.url"><a :href="source.url" target="_blank" rel="noreferrer">{{ source.name }}</a><p>{{ source.evidence }}</p></li></ul></section></article></main></template>
