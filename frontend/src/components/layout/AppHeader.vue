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
  { path: '/search', label: '搜索' },
  { path: '/graph', label: '图谱' },
  { path: '/encyclopedia', label: '百科' },
  { path: '/inheritors', label: '传承人' },
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
    class="heritage-header sticky top-0 z-50"
  >
    <div class="heritage-nav max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
      <!-- Logo — 极简 -->
      <router-link to="/" class="flex items-center gap-2 no-underline group">
        <img src="/favicon.svg?v=3" alt="" class="w-6 h-6" />
        <span class="brand-name group-hover:text-[var(--accent)] transition-colors">
          HeritageMind
        </span>
      </router-link>

      <!-- Nav — 克制、轻盈 -->
      <nav class="flex items-center gap-0.5">
        <router-link
          v-for="link in visibleNavLinks"
          :key="link.path"
          :to="link.path"
          class="nav-link px-3 py-1.5 text-[13px] font-medium transition-all duration-300 no-underline"
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

<style scoped>
.heritage-header { background: rgba(247, 239, 222, .88); border-bottom: 1px solid rgba(84, 61, 34, .16); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); }
.heritage-nav { position: relative; }.heritage-nav::after { content: ''; position: absolute; bottom: -1px; left: 24px; width: 88px; height: 2px; background: var(--accent); }
.brand-name { color: var(--text); font-family: 'Times New Roman', serif; font-size: 1.25rem; font-weight: 700; letter-spacing: .04em; }.nav-link { border-bottom: 2px solid transparent; }.nav-link.router-link-active { border-bottom-color: var(--accent); }
</style>
