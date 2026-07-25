import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosError } from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 300_000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: inject auth token + custom headers
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Auth token
  const token = localStorage.getItem('heritagemind_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }

  // Custom API key / model headers (user-provided)
  const userApiKey = localStorage.getItem('hm_user_api_key')
  const userBaseUrl = localStorage.getItem('hm_user_base_url')
  const selectedModel = localStorage.getItem('hm_selected_model')
  if (userApiKey && config.headers) {
    config.headers['X-API-Key'] = userApiKey
  }
  if (userBaseUrl && config.headers) {
    config.headers['X-API-Base'] = userBaseUrl
  }
  if (selectedModel && config.headers) {
    config.headers['X-Model'] = selectedModel
  }

  return config
})

// Response interceptor: handle 401
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('heritagemind_token')
      localStorage.removeItem('heritagemind_user')
    }
    return Promise.reject(error)
  },
)

export default client
