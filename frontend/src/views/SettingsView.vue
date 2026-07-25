<script setup lang="ts">
import { onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useChatStore } from '@/stores/chat'

const settings = useSettingsStore()
const chat = useChatStore()

onMounted(() => {
  settings.loadServerConfig()
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-6">
    <h2 class="text-2xl font-extrabold tracking-tight mb-1">系统设置</h2>
    <p class="text-[var(--text2)] mb-6">模型选择 · API Key · 偏好配置</p>

    <!-- Key Required Notice -->
    <div class="setting-section" style="background: #fafafa; border-color: var(--border)">
      <div class="flex items-start gap-3">
        <span class="text-2xl">💡</span>
        <div>
          <h3 style="color: var(--text); margin-bottom: 6px">填写 API Key 即可使用</h3>
          <p class="text-sm text-[var(--text2)] leading-relaxed">
            在下方填入你自己的 API Key，所有请求将使用你的额度，与服务器无关。
          </p>
        </div>
      </div>
    </div>

    <!-- Model Selector -->
    <div class="setting-section">
      <h3>🤖 模型选择</h3>

      <div class="mb-4">
        <label class="text-sm text-[var(--text2)] block mb-2">提供商</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="provider in settings.getProviders()"
            :key="provider"
            @click="settings.setProvider(provider)"
            class="px-4 py-2 rounded-full text-sm font-medium transition-all"
            :class="settings.selectedProvider === provider
              ? 'bg-[var(--text)] text-white'
              : 'bg-gray-100 text-[var(--text2)] hover:bg-gray-200'"
          >
            {{ provider }}
          </button>
        </div>
      </div>

      <div class="mb-4">
        <label class="text-sm text-[var(--text2)] block mb-1">API 地址</label>
        <input
          :value="settings.userBaseUrl"
          @input="settings.setBaseUrl(($event.target as HTMLInputElement).value)"
          placeholder="https://api.example.com/v1"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[var(--accent)] font-mono"
        />
      </div>

      <div class="mb-4">
        <label class="text-sm text-[var(--text2)] block mb-1">模型名称</label>
        <input
          :value="settings.selectedModel"
          @input="settings.setModel(($event.target as HTMLInputElement).value)"
          placeholder="输入模型名，如 deepseek-chat"
          class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[var(--accent)] font-mono"
        />
        <div v-if="settings.getProviderModels(settings.selectedProvider).length" class="flex flex-wrap gap-1.5 mt-2">
          <span class="text-xs text-[var(--text3)] mr-1 leading-6">推荐：</span>
          <button
            v-for="m in settings.getProviderModels(settings.selectedProvider)"
            :key="m"
            @click="settings.setModel(m)"
            class="px-2.5 py-0.5 rounded-full text-xs border transition-colors"
            :class="settings.selectedModel === m
              ? 'border-[var(--accent)] text-[var(--accent)] bg-orange-50'
              : 'border-[var(--border)] text-[var(--text2)] hover:border-[var(--accent)]'"
          >
            {{ m }}
          </button>
        </div>
      </div>

      <div class="text-xs text-[var(--text3)] bg-gray-50 rounded-lg px-3 py-2 mt-2">
        当前：
        <strong class="text-[var(--text)]">{{ settings.selectedModel }}</strong>
        @ {{ settings.userBaseUrl }}
        <template v-if="settings.hasCustomKey"> · Key 已配置</template>
        <template v-else> · 待配置 Key</template>
      </div>
    </div>

    <!-- API Key -->
    <div class="setting-section">
      <h3>🔑 API Key <span class="text-xs text-[var(--text3)] font-normal">（必填）</span></h3>
      <p class="text-sm text-[var(--text2)] mb-3">
        填入你自己的 API Key，请求将使用你的额度。Key 仅存储在浏览器中，不会上传到服务器。
      </p>
      <div class="flex gap-2">
        <input
          type="password"
          :value="settings.userApiKey"
          @input="settings.setApiKey(($event.target as HTMLInputElement).value)"
          placeholder="sk-..."
          class="flex-1 text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[var(--accent)] font-mono"
        />
        <button
          v-if="settings.hasCustomKey"
          @click="settings.clearApiKey()"
          class="px-4 py-2 text-sm text-red-500 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
        >
          清除
        </button>
      </div>
      <p v-if="settings.hasCustomKey" class="text-xs text-green-600 mt-2">
        ✅ 已设置 Key
      </p>
      <p v-else class="text-xs text-amber-600 mt-2">
        ⚠️ 未设置 Key — 暂时无法提问
      </p>
    </div>

    <!-- Preferences -->
    <div class="setting-section">
      <h3>👤 用户偏好</h3>
      <div class="flex flex-col gap-3">
        <div>
          <label class="text-sm text-[var(--text2)] block mb-1">默认学习深度</label>
          <select
            :value="settings.defaultProfile"
            @change="settings.setDefaultProfile(($event.target as HTMLSelectElement).value); chat.setProfile(($event.target as HTMLSelectElement).value)"
            class="w-full text-sm border border-[var(--border)] rounded-lg px-3 py-2 bg-white"
          >
            <option value="curious">好奇者（300-500字）</option>
            <option value="learner">学习者（800-1500字）</option>
            <option value="researcher">研究者（2000+字）</option>
          </select>
        </div>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            :checked="settings.defaultNarrative"
            @change="settings.setDefaultNarrative(($event.target as HTMLInputElement).checked); chat.includeNarrative = ($event.target as HTMLInputElement).checked"
            class="rounded"
          />
          <span class="text-sm">默认使用传承人口吻叙事</span>
        </label>
      </div>
    </div>

    <!-- About -->
    <div class="setting-section">
      <h3>📦 关于 HeritageMind</h3>
      <div class="text-sm text-[var(--text2)] leading-relaxed space-y-1">
        <p><b>版本</b>：v1.0.0</p>
        <p><b>架构</b>：FastAPI + LangGraph + Vue 3</p>
        <p><b>向量库</b>：ChromaDB + BM25 + RRF</p>
        <p><b>知识图谱</b>：NetworkX + pyvis</p>
        <p>
          <b>GitHub</b>：
          <a href="https://github.com/sunset9527/HeritageMind" target="_blank" class="text-[var(--accent)]">sunset9527/HeritageMind</a>
        </p>
      </div>
    </div>
  </div>
</template>
