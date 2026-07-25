import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import type { UserResponse } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('heritagemind_token'))
  const user = ref<UserResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const resp = await authApi.login(username, password)
      token.value = resp.access_token
      user.value = resp.user
      localStorage.setItem('heritagemind_token', resp.access_token)
      if (resp.user) {
        localStorage.setItem('heritagemind_user', JSON.stringify(resp.user))
      }
      return resp
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || '登录失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const resp = await authApi.register(username, email, password)
      token.value = resp.access_token
      user.value = resp.user
      localStorage.setItem('heritagemind_token', resp.access_token)
      if (resp.user) {
        localStorage.setItem('heritagemind_user', JSON.stringify(resp.user))
      }
      return resp
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || '注册失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('heritagemind_token')
    localStorage.removeItem('heritagemind_user')
  }

  async function restoreSession() {
    if (!token.value) return
    try {
      const u = await authApi.getMe()
      user.value = u
    } catch {
      // Token expired or invalid
      logout()
    }
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    restoreSession,
  }
})
