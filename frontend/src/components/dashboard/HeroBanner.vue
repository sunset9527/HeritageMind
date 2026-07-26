<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getCrafts } from '@/api/meta'

const craftCount = ref(23)

onMounted(async () => {
  try { const crafts = await getCrafts(); craftCount.value = crafts.length } catch { /* */ }
})
</script>

<template>
  <section class="hero" style="padding-bottom: 48px; position: relative; overflow: hidden">
    <div
      aria-hidden="true"
      style="
        position: absolute; inset: 0; pointer-events: none; z-index: 0;
        background:
          radial-gradient(ellipse 80% 60% at 50% 30%, rgba(196, 69, 54, 0.04) 0%, transparent 70%),
          radial-gradient(ellipse 60% 50% at 80% 70%, rgba(180, 140, 60, 0.03) 0%, transparent 70%),
          radial-gradient(ellipse 50% 40% at 20% 60%, rgba(90, 120, 90, 0.03) 0%, transparent 70%);
      "
    />
    <div style="position: relative; z-index: 1">
      <h1 class="calligraphy-title">
        让非遗被看见
      </h1>
      <p class="calligraphy-sub">
        {{ craftCount }} 种国家级非物质文化遗产，由多智能体协作守护。每一个问题，都是一次与千年技艺的对话。
      </p>
    </div>
  </section>
</template>

<style scoped>
.calligraphy-title {
  font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  font-size: clamp(3.5rem, 9vw, 7rem);
  font-weight: 400;
  line-height: 1.3;
  text-align: center;
  margin: 0 0 12px;
  color: #1C1C1E;
  letter-spacing: 0.08em;
  background: linear-gradient(180deg, #1a1a1a 0%, #2a2520 40%, #3a3028 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 1px 0 rgba(0,0,0,0.08), 2px 2px 4px rgba(0,0,0,0.04);
}

.calligraphy-sub {
  font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  font-size: 1.15rem;
  font-weight: 400;
  color: var(--text-secondary);
  line-height: 1.9;
  max-width: 600px;
  margin: 0 auto;
  letter-spacing: 0.04em;
}

@media (max-width: 640px) {
  .calligraphy-title { font-size: clamp(2.5rem, 11vw, 4rem); }
}
</style>
