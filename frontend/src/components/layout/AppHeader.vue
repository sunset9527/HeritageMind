<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const navLinks = [
  { path: '/', label: '首页' },
  { path: '/chat', label: '问答' },
  { path: '/graph', label: '图谱' },
  { path: '/media', label: '媒体' },
  { path: '/settings', label: '设置' },
]
const visibleNavLinks = computed(() => auth.user?.role === 'admin'
  ? [...navLinks, { path: '/admin', label: '管理' }]
  : navLinks)

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <header
    class="sticky top-0 z-50"
    style="background: rgba(249, 247, 244, 0.72); backdrop-filter: saturate(180%) blur(20px); -webkit-backdrop-filter: saturate(180%) blur(20px)"
  >
    <div class="max-w-6xl mx-auto px-6 h-13 flex items-center justify-between">
      <!-- Logo — 极简 -->
      <router-link to="/" class="flex items-center gap-2 no-underline group">
        <img src="/favicon.svg?v=3" alt="" class="w-6 h-6" />
        <span class="font-semibold text-[15px] tracking-tight text-[var(--text)] group-hover:text-[var(--accent)] transition-colors">
          HeritageMind
        </span>
      </router-link>

      <!-- Nav — 克制、轻盈 -->
      <nav class="flex items-center gap-0.5">
        <router-link
          v-for="link in visibleNavLinks"
          :key="link.path"
          :to="link.path"
          class="px-3.5 py-1.5 rounded-full text-[13px] font-medium transition-all duration-300 no-underline"
          :class="isActive(link.path)
            ? 'text-[var(--accent)]'
            : 'text-[var(--text-tertiary)] hover:text-[var(--text)]'"
        >
          {{ link.label }}
        </router-link>

        <span class="w-px h-4 mx-2" style="background: var(--border-strong)" />

        <!-- Auth -->
        <template v-if="auth.isAuthenticated">
          <span class="text-[13px] text-[var(--text-secondary)] ml-1">{{ auth.user?.username }}</span>
          <button
            @click="auth.logout()"
            class="ml-1 px-3 py-1 text-[12px] text-[var(--text-tertiary)] hover:text-[var(--accent)] rounded-full transition-colors"
          >
            退出
          </button>
        </template>
        <router-link
          v-else
          to="/login"
          class="ml-1 px-4 py-1.5 text-[13px] font-medium rounded-full transition-all no-underline"
          style="background: var(--text); color: #fff"
        >
          登录
        </router-link>
      </nav>
    </div>
  </header>
</template>
