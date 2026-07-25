<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')

async function handleLogin() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  try {
    await auth.login(username.value, password.value)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.message || '登录失败')
  }
}
</script>

<template>
  <div class="max-w-md mx-auto px-6 py-20">
    <div class="text-center mb-8">
      <span class="text-4xl">🏺</span>
      <h1 class="text-2xl font-extrabold tracking-tight mt-2">登录 HeritageMind</h1>
      <p class="text-sm text-[var(--text2)] mt-2">非遗知识平台</p>
    </div>

    <div class="card space-y-4">
      <div>
        <label class="text-sm text-[var(--text2)] block mb-1">用户名</label>
        <input
          v-model="username"
          @keyup.enter="handleLogin"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:border-[var(--accent)]"
          placeholder="输入用户名"
        />
      </div>
      <div>
        <label class="text-sm text-[var(--text2)] block mb-1">密码</label>
        <input
          v-model="password"
          type="password"
          @keyup.enter="handleLogin"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:border-[var(--accent)]"
          placeholder="输入密码"
        />
      </div>
      <button
        @click="handleLogin"
        :disabled="auth.loading"
        class="w-full py-2.5 rounded-full bg-[var(--text)] text-white font-semibold text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
      >
        {{ auth.loading ? '登录中…' : '登录' }}
      </button>
    </div>

    <p class="text-center text-sm text-[var(--text2)] mt-4">
      还没有账号？
      <router-link to="/register" class="text-[var(--accent)] font-medium no-underline">注册</router-link>
    </p>
  </div>
</template>
