<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useChatStore } from '@/stores/chat'
import { ElMessage } from 'element-plus'

const settings = useSettingsStore()
const chat = useChatStore()

// 本地编辑状态（修改后才同步到 store + localStorage）
const form = reactive({
  provider: settings.selectedProvider,
  model: settings.selectedModel,
  apiKey: settings.userApiKey,
  baseUrl: settings.userBaseUrl,
  profile: settings.defaultProfile,
  narrative: settings.defaultNarrative,
})

const PROVIDER_INFO: Record<string, { noKey: boolean }> = {}

onMounted(() => { settings.loadServerConfig() })

function saveSettings() {
  settings.setProvider(form.provider)
  settings.setModel(form.model)
  if (form.apiKey) settings.setApiKey(form.apiKey)
  if (form.baseUrl) settings.setBaseUrl(form.baseUrl)
  settings.setDefaultProfile(form.profile)
  settings.setDefaultNarrative(form.narrative)
  chat.setProfile(form.profile)
  chat.includeNarrative = form.narrative
  settings.save()
  ElMessage.success('设置已保存')
}
</script>

<template>
  <div class="heritage-page max-w-3xl mx-auto px-6 py-10">
    <p class="page-kicker">使用偏好</p>
    <h1 class="page-title">系统设置</h1>
    <p class="page-intro">模型选择 · API Key · 偏好配置</p>

    <!-- Notice -->
    <div class="setting-section" style="background: #fafafa; border-color: var(--border)">
      <div class="flex items-start gap-3">
        <span class="text-2xl">💡</span>
        <div>
          <h3 style="color: var(--text); margin-bottom: 6px">需要 API Key 才能使用</h3>
          <p class="text-sm text-[var(--text2)] leading-relaxed">
            在下方填入你自己的 API Key，所有请求将使用你的额度，与服务器无关。配置完成后点击底部「保存设置」。
          </p>
        </div>
      </div>
    </div>

    <!-- Model -->
    <div class="setting-section">
      <h3>🤖 模型选择</h3>
      <div class="mb-4">
        <label class="text-sm text-[var(--text2)] block mb-2">提供商</label>
        <div class="flex flex-wrap gap-2">
          <button v-for="p in settings.getProviders()" :key="p"
            @click="form.provider = p; form.baseUrl = settings.getProviderBaseUrl(p); if (settings.getProviderModels(p).length) form.model = settings.getProviderModels(p)[0]"
            class="px-4 py-2 rounded-full text-sm font-medium transition-all"
            :class="form.provider === p ? 'bg-[var(--text)] text-white' : 'bg-gray-100 text-[var(--text2)] hover:bg-gray-200'">
            {{ p }}
          </button>
        </div>
      </div>
      <div class="mb-4">
        <label class="text-sm text-[var(--text2)] block mb-1">API 地址</label>
        <input v-model="form.baseUrl" placeholder="https://api.example.com/v1"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[var(--accent)] font-mono" />
      </div>
      <div class="mb-4">
        <label class="text-sm text-[var(--text2)] block mb-1">模型名称</label>
        <input v-model="form.model" placeholder="deepseek-chat"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[var(--accent)] font-mono" />
        <div v-if="settings.getProviderModels(form.provider).length" class="flex flex-wrap gap-1.5 mt-2">
          <span class="text-xs text-[var(--text3)] mr-1 leading-6">推荐：</span>
          <button v-for="m in settings.getProviderModels(form.provider)" :key="m"
            @click="form.model = m"
            class="px-2.5 py-0.5 rounded-full text-xs border transition-colors"
            :class="form.model === m ? 'border-[var(--accent)] text-[var(--accent)] bg-orange-50' : 'border-[var(--border)] text-[var(--text2)] hover:border-[var(--accent)]'">
            {{ m }}
          </button>
        </div>
      </div>
    </div>

    <!-- API Key -->
    <div class="setting-section">
      <h3>🔑 API Key <span class="text-xs text-[var(--text3)] font-normal">（必填）</span></h3>
      <p class="text-sm text-[var(--text2)] mb-3">Key 仅存储在浏览器中，不会上传到服务器。</p>
      <input v-model="form.apiKey" type="password" placeholder="sk-..."
        class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[var(--accent)] font-mono" />
      <p v-if="form.apiKey" class="text-xs text-green-600 mt-2">✅ 已填写（{{ form.apiKey.slice(0, 10) }}...）</p>
      <p v-else class="text-xs text-amber-600 mt-2">⚠️ 未填写 — 暂时无法提问</p>
    </div>

    <!-- Preferences -->
    <div class="setting-section">
      <h3>👤 用户偏好</h3>
      <div class="flex flex-col gap-3">
        <div>
          <label class="text-sm text-[var(--text2)] block mb-1">默认学习深度</label>
          <select v-model="form.profile"
            class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white">
            <option value="curious">好奇者（300-500字）</option>
            <option value="learner">学习者（800-1500字）</option>
            <option value="researcher">研究者（2000+字）</option>
          </select>
        </div>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="form.narrative" class="rounded" />
          <span class="text-sm">默认使用传承人口吻叙事</span>
        </label>
      </div>
    </div>

    <!-- Save -->
    <div class="text-center">
      <button @click="saveSettings"
        class="px-12 py-3 rounded-full text-white font-semibold text-sm transition-all border-0 cursor-pointer"
        style="background: var(--accent); box-shadow: 0 2px 8px rgba(196,69,54,0.3)"
      >
        保存设置
      </button>
    </div>

    <!-- About -->
    <div class="setting-section mt-4">
      <h3>📦 关于 HeritageMind</h3>
      <div class="text-sm text-[var(--text2)] leading-relaxed space-y-1">
        <p><b>版本</b>：v1.3.0</p>
        <p><b>架构</b>：FastAPI + LangGraph + Vue 3</p>
        <p><b>数据库</b>：MySQL</p>
        <p><b>知识库</b>：23 种非遗技艺</p>
        <p><b>GitHub</b>：<a href="https://github.com/sunset9527/HeritageMind" target="_blank" class="text-[var(--accent)]">sunset9527/HeritageMind</a></p>
      </div>
    </div>
  </div>
</template>
