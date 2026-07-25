<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const features = [
  { icon: '💬', title: 'AI 问答', desc: '三专家 Agent 协作 · 辩论引擎 · 知识缺口检测', route: '/chat' },
  { icon: '🕸️', title: '知识图谱', desc: '技艺 · 材料 · 工具 · 传承人 · 地域 · 朝代', route: '/graph' },
  { icon: '⚙️', title: '偏好设置', desc: '选择模型 · 配置 API Key · 调整学习深度', route: '/settings' },
]
</script>

<template>
  <section class="max-w-5xl mx-auto px-6 mb-20" style="font-family: 'Ma Shan Zheng', 'STKaiti', 'KaiTi', 'PingFang SC', serif">
    <p class="caption uppercase tracking-wider mb-4" style="font-size: 0.7rem; letter-spacing: 0.08em; font-family: 'Inter', 'PingFang SC', sans-serif">探索方式</p>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <button
        v-for="f in features"
        :key="f.title"
        @click="router.push(f.route)"
        class="card text-left border-0 cursor-pointer group"
      >
        <div class="text-[28px] mb-4">{{ f.icon }}</div>
        <h3 class="title mb-1.5 group-hover:text-[var(--accent)] transition-colors">{{ f.title }}</h3>
        <p class="body text-[14px]">{{ f.desc }}</p>
      </button>
    </div>
  </section>
</template>
