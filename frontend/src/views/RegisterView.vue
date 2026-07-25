<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')

async function handleRegister() {
  if (!username.value || !email.value || !password.value) {
    ElMessage.warning('请完整填写所有字段')
    return
  }
  if (password.value.length < 6) {
    ElMessage.warning('密码长度至少 6 位')
    return
  }
  try {
    await auth.register(username.value, email.value, password.value)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.message || '注册失败')
  }
}
</script>

<template>
  <div class="max-w-md mx-auto px-6 py-20">
    <div class="text-center mb-8">
      <span class="text-4xl">🏺</span>
      <h1 class="text-2xl font-extrabold tracking-tight mt-2">注册 HeritageMind</h1>
      <p class="text-sm text-[var(--text2)] mt-2">非遗知识平台</p>
    </div>

    <div class="card space-y-4">
      <div>
        <label class="text-sm text-[var(--text2)] block mb-1">用户名</label>
        <input
          v-model="username"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:border-[var(--accent)]"
          placeholder="2-50 个字符"
        />
      </div>
      <div>
        <label class="text-sm text-[var(--text2)] block mb-1">邮箱</label>
        <input
          v-model="email"
          type="email"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:border-[var(--accent)]"
          placeholder="your@email.com"
        />
      </div>
      <div>
        <label class="text-sm text-[var(--text2)] block mb-1">密码</label>
        <input
          v-model="password"
          type="password"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:border-[var(--accent)]"
          placeholder="至少 6 位"
        />
      </div>
      <button
        @click="handleRegister"
        :disabled="auth.loading"
        class="w-full py-2.5 rounded-full bg-[var(--accent)] text-white font-semibold text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
      >
        {{ auth.loading ? '注册中…' : '注册' }}
      </button>
    </div>

    <p class="text-center text-sm text-[var(--text2)] mt-4">
      已有账号？
      <router-link to="/login" class="text-[var(--accent)] font-medium no-underline">登录</router-link>
    </p>
  </div>
</template>
