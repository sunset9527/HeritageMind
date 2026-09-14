<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getSessions } from '@/api/chat'
const sessions = ref<any[]>([]); const error = ref('')
onMounted(async () => { try { sessions.value = (await getSessions()).items } catch { error.value = '请登录后查看个人中心。' } })
</script>
<template><main class="heritage-page max-w-5xl mx-auto px-6 py-10"><p class="page-kicker">个人档案</p><h1 class="page-title">个人中心</h1><p class="page-intro">会话、收藏、偏好与模型设置的统一入口。</p><p v-if="error">{{ error }}</p><section v-else class="setting-section"><h2>最近会话</h2><p v-if="!sessions.length">暂无会话记录。</p><ul v-else><li v-for="item in sessions" :key="item.id">{{ item.title || item.id }}</li></ul></section><router-link to="/settings" class="mt-4 inline-block">前往模型与 API Key 设置 →</router-link></main></template>
