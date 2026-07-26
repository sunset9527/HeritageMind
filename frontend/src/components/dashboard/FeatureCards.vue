<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const features = [
  { icon: '💬', title: 'AI 问答', route: '/chat' },
  { icon: '🕸️', title: '知识图谱', route: '/graph' },
  { icon: '⚙️', title: '偏好设置', route: '/settings' },
]
</script>

<template>
  <section class="max-w-5xl mx-auto px-6 mb-20">
    <div class="flex items-center justify-center gap-2">
      <button
        v-for="f in features"
        :key="f.title"
        @click="router.push(f.route)"
        class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-[13px] font-medium transition-all duration-300 cursor-pointer border-0"
        style="background: var(--surface); color: var(--text-secondary); box-shadow: var(--shadow-sm); border: 1px solid var(--border)"
      >
        <span>{{ f.icon }}</span>
        <span>{{ f.title }}</span>
      </button>
    </div>
  </section>
</template>
