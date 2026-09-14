<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const chat = useChatStore()
const question = ref('')

function startExploring() {
  const value = question.value.trim()
  if (!value) return
  chat.setPendingQuestion(value)
  router.push('/chat')
}
</script>

<template>
  <section class="heritage-hero">
    <div class="hero-copy">
      <p class="hero-kicker">一 · 非遗文化智能知识平台</p>
      <h1>以<span>技艺</span>为经<br />让传承可见</h1>
      <p class="hero-intro">从一件器物、一段唱腔到一门手艺的历史脉络。检索、图谱与多智能体协作，将知识的来处和答案一并呈现。</p>
      <form class="hero-search" @submit.prevent="startExploring">
        <label class="sr-only" for="heritage-question">输入你想了解的非遗问题</label>
        <input id="heritage-question" v-model="question" placeholder="想了解哪一门手艺？" />
        <button type="submit">开始寻艺</button>
      </form>
    </div>
    <div class="hero-art" aria-label="景泰蓝工艺展示">
      <img src="/crafts/景泰蓝.jpg" alt="景泰蓝工艺作品" />
      <div class="enamel-wire" aria-hidden="true" />
      <p>铜丝为骨 · 珐琅成彩</p>
    </div>
  </section>
</template>

<style scoped>
.heritage-hero { display: grid; grid-template-columns: minmax(0, 1.06fr) minmax(330px, .94fr); max-width: 1120px; min-height: 470px; margin: 44px auto 0; overflow: hidden; border: 1px solid rgba(89, 67, 41, .2); background: #efe4ce; box-shadow: 0 18px 44px rgba(76, 49, 23, .12); }
.hero-copy { padding: 76px 52px 52px 62px; background: linear-gradient(135deg, #f7efdf 0%, #eee1c8 100%); }
.hero-kicker { margin: 0 0 16px; color: var(--accent); font-size: .68rem; font-weight: 700; letter-spacing: .22em; }
h1 { margin: 0; color: #26322d; font-family: var(--font-brush); font-size: clamp(3.8rem, 7vw, 5.8rem); font-weight: 400; letter-spacing: .12em; line-height: .98; transform: rotate(-1deg); transform-origin: left center; }
h1 span { color: var(--accent); }
.hero-intro { max-width: 390px; margin: 28px 0 24px; color: #5e5549; font-size: .9rem; line-height: 2; }
.hero-search { display: flex; max-width: 400px; border-bottom: 1px solid #776657; gap: 12px; padding: 9px 0; }
.hero-search input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: var(--text); font: inherit; }
.hero-search input::placeholder { color: #8b7d6e; }
.hero-search button { border: 0; border-radius: 2px; background: var(--accent); color: #fff6e4; cursor: pointer; padding: 8px 14px; font-size: .78rem; letter-spacing: .08em; }
.hero-art { position: relative; overflow: hidden; background: #1d6878; }
.hero-art::after { content: ''; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(21, 56, 59, .45), transparent 48%), linear-gradient(0deg, rgba(13, 52, 61, .3), transparent 55%); }
.hero-art img { width: 100%; height: 100%; object-fit: cover; filter: saturate(.82) contrast(1.04); }
.enamel-wire { position: absolute; inset: 30px; z-index: 1; border: 1px solid rgba(237, 205, 123, .9); clip-path: polygon(50% 0, 61% 20%, 84% 15%, 73% 36%, 100% 50%, 73% 63%, 84% 84%, 61% 79%, 50% 100%, 39% 79%, 16% 84%, 27% 63%, 0 50%, 27% 36%, 16% 15%, 39% 20%); filter: drop-shadow(0 0 3px rgba(255, 225, 148, .8)); }
.hero-art p { position: absolute; z-index: 2; right: 27px; bottom: 36px; margin: 0; color: #fff1cf; font-family: var(--font-brush); font-size: 2.5rem; letter-spacing: .2em; line-height: 1.35; text-shadow: 0 2px 5px rgba(0, 0, 0, .55); writing-mode: vertical-rl; }
@media (max-width: 760px) { .heritage-hero { grid-template-columns: 1fr; margin-top: 24px; } .hero-copy { padding: 52px 30px 42px; } .hero-art { min-height: 280px; } h1 { font-size: 4.5rem; } }
</style>
