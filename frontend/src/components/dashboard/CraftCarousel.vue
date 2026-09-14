<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listEncyclopedia, type CraftEntry } from '@/api/platform'
const entries = ref<CraftEntry[]>([])
onMounted(async () => { try { entries.value = (await listEncyclopedia()).slice(0, 4) } catch { /* Hidden until content is available. */ } })
</script>
<template>
  <section v-if="entries.length" class="craft-section">
    <div class="section-heading"><div><p>二 · 从一门技艺开始</p><h2>工艺的细节，值得被慢慢读懂</h2></div><router-link to="/encyclopedia">浏览全部技艺</router-link></div>
    <div class="craft-grid"><router-link v-for="entry in entries" :key="entry.slug" :to="`/encyclopedia/${entry.slug}`" class="craft-card"><img :src="`/crafts/${entry.name}.jpg`" :alt="entry.name" /><div class="craft-overlay"><h3>{{ entry.name }}</h3><p>{{ entry.summary }}</p><span>阅读条目 →</span></div></router-link></div>
  </section>
</template>
<style scoped>
.craft-section{max-width:1120px;margin:0 auto 76px;padding:0 24px}.section-heading{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:22px}.section-heading p{color:var(--accent);font-size:.67rem;font-weight:700;letter-spacing:.2em;margin:0 0 7px}.section-heading h2{margin:0;font-family:var(--font-brush);font-size:2.2rem;font-weight:400;letter-spacing:.1em}.section-heading a{color:var(--accent);font-size:.8rem;text-decoration:none;white-space:nowrap}.craft-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.craft-card{position:relative;min-height:265px;overflow:hidden;background:#1d6878;color:#fff8e7;text-decoration:none}.craft-card::after{content:'';position:absolute;inset:0;background:linear-gradient(0deg,rgba(12,34,32,.86),rgba(12,34,32,.05) 70%)}.craft-card img{width:100%;height:100%;position:absolute;object-fit:cover;filter:saturate(.75);transition:transform .35s ease}.craft-card:hover img{transform:scale(1.05)}.craft-overlay{position:absolute;inset:auto 16px 16px;z-index:1}.craft-overlay h3{margin:0 0 6px;font-family:var(--font-brush);font-size:2rem;font-weight:400;letter-spacing:.1em}.craft-overlay p{display:-webkit-box;overflow:hidden;margin:0 0 12px;color:#f7ecd7;font-size:.72rem;line-height:1.6;-webkit-box-orient:vertical;-webkit-line-clamp:2}.craft-overlay span{color:#edc875;font-size:.7rem;letter-spacing:.08em}@media(max-width:820px){.craft-grid{grid-template-columns:repeat(2,1fr)}.section-heading h2{font-size:1.9rem}}@media(max-width:480px){.craft-section{padding:0 18px}.craft-grid{grid-template-columns:1fr}.section-heading{align-items:start;flex-direction:column}.craft-card{min-height:230px}}
</style>
