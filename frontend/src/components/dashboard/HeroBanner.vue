<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useGraphStore } from '@/stores/graph'
import { getCrafts } from '@/api/meta'

const graphStore = useGraphStore()
const craftCount = ref(23)

onMounted(async () => {
  graphStore.fetchStats()
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
      <!-- 毛笔字标题 -->
      <h1 class="calligraphy-title">
        让非遗被看见
      </h1>
      <p class="calligraphy-sub">
        {{ craftCount }} 种国家级非物质文化遗产，由多智能体协作守护。每一个问题，都是一次与千年技艺的对话。
      </p>
      <div class="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
        <div>
          <div style="font-size: 2rem; font-weight: 700; color: var(--text); letter-spacing: -0.03em; line-height: 1">
            {{ craftCount }}<span style="font-size: 0.85rem; font-weight: 400; color: var(--text-tertiary); margin-left: 2px"> 种</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-tertiary); margin-top: 4px">非遗技艺</div>
        </div>
        <div>
          <div style="font-size: 2rem; font-weight: 700; color: var(--text); letter-spacing: -0.03em; line-height: 1">
            {{ graphStore.stats?.total_nodes ?? 65 }}<span style="font-size: 0.85rem; font-weight: 400; color: var(--text-tertiary); margin-left: 2px"> 个</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-tertiary); margin-top: 4px">知识节点</div>
        </div>
        <div>
          <div style="font-size: 2rem; font-weight: 700; color: var(--text); letter-spacing: -0.03em; line-height: 1">
            {{ graphStore.stats?.total_edges ?? 39 }}<span style="font-size: 0.85rem; font-weight: 400; color: var(--text-tertiary); margin-left: 2px"> 条</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-tertiary); margin-top: 4px">语义关联</div>
        </div>
        <div>
          <div style="font-size: 2rem; font-weight: 700; color: var(--text); letter-spacing: -0.03em; line-height: 1">
            3<span style="font-size: 0.85rem; font-weight: 400; color: var(--text-tertiary); margin-left: 2px"> 位</span>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-tertiary); margin-top: 4px">专家 Agent</div>
        </div>
      </div>
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
  /* 墨色渐变：浓墨 → 淡墨 */
  background: linear-gradient(
    180deg,
    #1a1a1a 0%,
    #2a2520 40%,
    #3a3028 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  /* 毛笔枯笔飞白效果 */
  text-shadow:
    0 1px 0 rgba(0,0,0,0.08),
    2px 2px 4px rgba(0,0,0,0.04);
}

.calligraphy-sub {
  font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  font-size: 1.15rem;
  font-weight: 400;
  color: var(--text-secondary);
  line-height: 1.9;
  max-width: 600px;
  margin: 0 auto 48px;
  letter-spacing: 0.04em;
}

@media (max-width: 640px) {
  .calligraphy-title {
    font-size: clamp(2.5rem, 11vw, 4rem);
  }
}
</style>
