<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { getCrafts, getDocumentSummary, type DocumentSummary } from '@/api/meta'
import type { CraftItem } from '@/types'

const router = useRouter()
const chat = useChatStore()
const question = ref('')
const crafts = ref<CraftItem[]>()
const summary = ref<DocumentSummary>()

const knowledgeProof = computed(() => [
  { value: typeof summary.value?.total_documents === 'number' ? String(summary.value.total_documents) : '—', label: '已加载文档' },
  { value: crafts.value ? String(crafts.value.length) : '—', label: '非遗项目' },
  { value: '可核查', label: '资料治理' },
])

onMounted(async () => {
  try { crafts.value = await getCrafts() } catch { /* Show an honest placeholder until the catalog is available. */ }
  try { summary.value = await getDocumentSummary() } catch { /* Show an honest placeholder until the summary is available. */ }
})

function startExploring() {
  const value = question.value.trim()
  if (!value) return
  chat.setPendingQuestion(value)
  router.push('/chat')
}
</script>

<template>
  <section class="editorial-hero" aria-labelledby="hero-title">
    <div class="hero-copy">
      <p class="hero-kicker">CHINESE INTANGIBLE CULTURAL HERITAGE</p>
      <h1 id="hero-title">让传统拥有<br><em>可被追溯的现在</em></h1>
      <p class="hero-intro">从一门技艺出发，沿着机构、地域与传承人的资料脉络，理解它如何被创造、保存与继续使用。</p>
      <form class="hero-search" @submit.prevent="startExploring">
        <label class="sr-only" for="heritage-question">输入你想了解的非遗问题</label>
        <input id="heritage-question" v-model="question" placeholder="搜索一门技艺、人物或问题" />
        <button type="submit">开始探索 <span aria-hidden="true">→</span></button>
      </form>
      <dl data-testid="knowledge-proof" class="knowledge-proof" aria-label="平台知识库规模">
        <div v-for="item in knowledgeProof" :key="item.label"><dt>{{ item.value }}</dt><dd>{{ item.label }}</dd></div>
      </dl>
    </div>
    <figure class="hero-art">
      <img data-testid="hero-art-image" src="/editorial/hero-archive-textile-v1.png" alt="靛染线轴和织物越出乡村织造照片的编辑式艺术主视觉">
      <figcaption>从材料，到技艺，到被看见的传承</figcaption>
    </figure>
  </section>
</template>

<style scoped>
.editorial-hero { display:grid; grid-template-columns:minmax(0,1fr) minmax(390px,.94fr); max-width:1120px; min-height:568px; margin:34px auto 0; overflow:hidden; background:#1c2016; color:#f4f0e7; }
.hero-copy { display:flex; flex-direction:column; justify-content:center; padding:74px 46px 58px 66px; }
.hero-kicker { margin:0 0 19px; color:#c8aa73; font-size:.66rem; font-weight:700; letter-spacing:.2em; }
h1 { margin:0; font-family:var(--font-sans); font-size:clamp(2.25rem,3.4vw,3.6rem); font-weight:400; letter-spacing:.025em; line-height:1.18; }
h1 em { color:#e7dfca; font-style:normal; }
.hero-intro { max-width:410px; margin:27px 0 25px; color:#c3c8bc; font-size:.91rem; line-height:1.9; }
.hero-search { display:flex; align-items:center; max-width:445px; border-bottom:1px solid rgba(235,231,214,.54); gap:15px; padding:9px 0; }
.hero-search input { min-width:0; flex:1; border:0; outline:0; background:transparent; color:#f6f2e9; font:inherit; }
.hero-search input::placeholder { color:#adb4a8; }
.hero-search button { border:0; background:transparent; color:#d4b77e; cursor:pointer; font:inherit; font-size:.79rem; letter-spacing:.05em; padding:7px 0; }
.hero-search button:hover,.hero-search button:focus-visible { color:#fff0cb; outline:none; }.hero-search button:focus-visible { outline:2px solid #d4b77e; outline-offset:4px; }
.knowledge-proof { display:flex; flex-wrap:wrap; gap:0; margin:43px 0 0; }.knowledge-proof div { min-width:103px; padding:0 17px; border-left:1px solid rgba(210,204,184,.32); }.knowledge-proof div:first-child { padding-left:0; border-left:0; }
dt { color:#d4b77e; font-family:var(--font-sans); font-size:1.65rem; line-height:1.15; }dd { margin:4px 0 0; color:#bdc5ba; font-size:.66rem; letter-spacing:.06em; }
.hero-art { position:relative; display:grid; place-items:center; min-height:100%; margin:0; overflow:hidden; }.hero-art::after { content:''; position:absolute; inset:0; background:linear-gradient(90deg,#1c2016 0%,transparent 25%,rgba(20,23,17,.08)); pointer-events:none; }.hero-art img { width:100%; height:100%; min-height:568px; object-fit:contain; object-position:center; display:block; }figcaption { position:absolute; right:31px; bottom:29px; z-index:1; color:rgba(245,240,227,.83); font-size:.68rem; letter-spacing:.12em; }
@media (max-width:820px) { .editorial-hero { grid-template-columns:1fr; margin-top:18px; }.hero-copy { padding:55px 30px 45px; }.hero-art { min-height:360px; }.hero-art img { min-height:360px; } }
@media (max-width:460px) { .hero-copy { padding:48px 22px 42px; }.knowledge-proof { margin-top:35px; }.knowledge-proof div { min-width:92px; padding:0 10px; }.knowledge-proof div:first-child { padding-left:0; } }
</style>
