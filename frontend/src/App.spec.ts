// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import App from './App.vue'
import router from './router'

vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => ({ loadServerConfig: vi.fn() }),
}))

vi.mock('@/views/LoginView.vue', () => ({
  default: { template: '<div data-testid="login-view" />' },
}))

describe('public route editorial scenes', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.scrollTo = vi.fn()
  })

  it('places authentication routes in the clay workshop scene', async () => {
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(App, { global: { plugins: [createPinia(), router] } })

    expect(wrapper.find('[data-scene="clay"]').exists()).toBe(true)
    expect(wrapper.find('.scene-artwork').exists()).toBe(false)
  })
})
