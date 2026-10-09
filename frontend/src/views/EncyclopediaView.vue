<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { listEncyclopedia, type CraftEntry } from '@/api/platform'
import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
const entries = ref<CraftEntry[]>([])
const error = ref('')
const loading = ref(true)
let controller: AbortController | null = null

async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = ''
  try {
    entries.value = await listEncyclopedia({ signal: request.signal })
  } catch {
    if (!request.signal.aborted) error.value = '百科暂时不可用，请检查服务后重试。'
  } finally {
    if (controller === request) {
      loading.value = false
      controller = null
    }
  }
}

onMounted(load)
onBeforeUnmount(() => controller?.abort())
</script>
<template><main class="encyclopedia"><header><p>技艺百科</p><h1>循着工艺，读见传承</h1><span>条目、类别与来源证据均来自当前活动图书语料。</span></header><p v-if="loading" class="state" role="status">正在加载百科条目…</p><p v-else-if="error" class="state error">{{ error }} <button type="button" @click="load">重新加载</button></p><p v-else-if="!entries.length" class="state">当前图书语料暂未生成百科条目。</p><div v-else class="entries"><router-link v-for="entry in entries" :key="entry.slug" :to="`/encyclopedia/${entry.slug}`"><EncyclopediaImage class="entry-image" :name="entry.name" :image="entry.image"/><div class="entry-copy"><h2 class="entry-card-title">{{ entry.name }}</h2><p class="entry-card-summary">{{ entry.summary }}</p><span>阅读条目 →</span></div></router-link></div></main></template>
<style scoped>.encyclopedia{max-width:1120px;margin:auto;padding:58px 24px 86px}.encyclopedia header{margin-bottom:32px}.encyclopedia header>p{margin:0 0 7px;color:var(--accent);font-size:.7rem;font-weight:700;letter-spacing:.2em}.encyclopedia h1{margin:0;font-family:var(--font-brush);font-size:3.4rem;font-weight:400;letter-spacing:.12em}.encyclopedia header>span{display:block;margin-top:12px;color:var(--text-secondary);font-size:.85rem}.entries{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.entries a{overflow:hidden;background:#f7f1e5;border:1px solid rgba(82,61,36,.24);color:#283023;text-decoration:none}.entries :deep(.entry-image){height:185px}.entry-copy{padding:19px}.entry-card-title{margin:0;color:#293025;font-family:var(--font-brush);font-size:2rem;font-weight:400;letter-spacing:.1em}.entry-card-summary{display:-webkit-box;overflow:hidden;min-height:48px;margin:9px 0 15px;color:#465044;font-family:var(--font-sans);font-size:.9rem;font-weight:500;line-height:1.8;-webkit-box-orient:vertical;-webkit-line-clamp:2}.entries span{color:#7c5d27;font-size:.82rem;font-weight:700}.state{color:var(--text-tertiary)}.state button{margin-left:10px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;padding:4px 9px}.error{color:#b33d30}@media(max-width:760px){.entries{grid-template-columns:repeat(2,1fr)}.encyclopedia h1{font-size:2.7rem}}@media(max-width:480px){.encyclopedia{padding:36px 18px 60px}.entries{grid-template-columns:1fr}}</style>
