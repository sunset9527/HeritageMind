<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const chatStore = useChatStore()

const questions = [
  '景泰蓝的制作流程分为几步？',
  '苏绣有哪些著名传承人？',
  '龙泉青瓷的釉色形成原理是什么？',
]

function ask(q: string) {
  chatStore.setPendingQuestion(q)
  router.push('/chat')
}
</script>

<template>
  <section class="max-w-5xl mx-auto px-6 mb-20">
    <p class="caption uppercase tracking-wider mb-4" style="font-size: 0.7rem; letter-spacing: 0.08em">试着问问</p>
    <div class="flex flex-wrap gap-2.5">
      <button
        v-for="q in questions"
        :key="q"
        @click="ask(q)"
        class="px-5 py-2.5 rounded-full text-[14px] font-medium transition-all duration-300 cursor-pointer border-0"
        style="background: var(--surface); color: var(--text-secondary); box-shadow: var(--shadow-sm); border: 1px solid var(--border)"
      >
        {{ q }}
      </button>
    </div>
  </section>
</template>
