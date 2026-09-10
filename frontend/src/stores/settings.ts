import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getServerConfig, type ServerConfig } from '@/api/config'

const PROVIDER_PRESETS: Record<string, { baseUrl: string; models: string[] }> = {
  DeepSeek: {
    baseUrl: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-reasoner'],
  },
  OpenAI: {
    baseUrl: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1'],
  },
  Qwen: {
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-max', 'qwen-plus', 'qwen-turbo'],
  },
  Claude: {
    baseUrl: 'https://api.anthropic.com/v1',
    models: ['claude-sonnet-5', 'claude-opus-4-8', 'claude-haiku-4-5'],
  },
  Other: {
    baseUrl: '',
    models: [],
  },
}

export const useSettingsStore = defineStore('settings', () => {
  const serverConfig = ref<ServerConfig | null>(null)
  const serverConfigLoaded = ref(false)

  const selectedProvider = ref(localStorage.getItem('hm_provider') || 'DeepSeek')
  const selectedModel = ref(localStorage.getItem('hm_selected_model') || 'deepseek-chat')
  const userApiKey = ref(localStorage.getItem('hm_user_api_key') || '')
  const userBaseUrl = ref(localStorage.getItem('hm_user_base_url') || PROVIDER_PRESETS['DeepSeek'].baseUrl)
  const defaultProfile = ref(localStorage.getItem('hm_default_profile') || 'curious')
  const defaultNarrative = ref(localStorage.getItem('hm_default_narrative') === 'true')
  const hasCustomKey = ref(!!userApiKey.value)

  function canQuery(): boolean {
    return hasCustomKey.value
  }

  async function loadServerConfig() {
    try {
      const cfg = await getServerConfig()
      serverConfig.value = cfg
      serverConfigLoaded.value = true
      if (!localStorage.getItem('hm_selected_model')) {
        selectedModel.value = cfg.model
      }
      if (!localStorage.getItem('hm_provider')) {
        selectedProvider.value = cfg.provider
      }
      if (!localStorage.getItem('hm_user_base_url')) {
        userBaseUrl.value = cfg.base_url
      }
    } catch {
      serverConfigLoaded.value = true
    }
  }

  function getProviders(): string[] {
    return Object.keys(PROVIDER_PRESETS)
  }

  function getProviderModels(provider: string): string[] {
    return PROVIDER_PRESETS[provider]?.models || []
  }

  function getProviderBaseUrl(provider: string): string {
    return PROVIDER_PRESETS[provider]?.baseUrl || ''
  }

  function setProvider(provider: string) {
    selectedProvider.value = provider
    const info = PROVIDER_PRESETS[provider]
    if (info) {
      userBaseUrl.value = info.baseUrl
      if (info.models.length > 0) {
        selectedModel.value = info.models[0]
      }
    }
    if (provider === 'Other') {
      userBaseUrl.value = ''
      selectedModel.value = ''
    }
    save()
  }

  function setModel(model: string) {
    selectedModel.value = model
    save()
  }

  function setBaseUrl(url: string) {
    userBaseUrl.value = url
    save()
  }

  function setApiKey(key: string) {
    userApiKey.value = key
    hasCustomKey.value = !!key
    save()
  }

  function clearApiKey() {
    userApiKey.value = ''
    hasCustomKey.value = false
    save()
  }

  function setDefaultProfile(profile: string) {
    defaultProfile.value = profile
    save()
  }

  function setDefaultNarrative(val: boolean) {
    defaultNarrative.value = val
    save()
  }

  function save() {
    localStorage.setItem('hm_provider', selectedProvider.value)
    localStorage.setItem('hm_selected_model', selectedModel.value)
    localStorage.setItem('hm_user_api_key', userApiKey.value)
    localStorage.setItem('hm_user_base_url', userBaseUrl.value)
    localStorage.setItem('hm_default_profile', defaultProfile.value)
    localStorage.setItem('hm_default_narrative', String(defaultNarrative.value))
  }

  return {
    serverConfig,
    serverConfigLoaded,
    selectedProvider,
    selectedModel,
    userApiKey,
    userBaseUrl,
    defaultProfile,
    defaultNarrative,
    hasCustomKey,
    canQuery,
    loadServerConfig,
    getProviders,
    getProviderModels,
    getProviderBaseUrl,
    setProvider,
    setModel,
    setBaseUrl,
    setApiKey,
    clearApiKey,
    setDefaultProfile,
    setDefaultNarrative,
    save,
  }
})
