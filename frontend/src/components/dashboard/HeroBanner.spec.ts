// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import HeroBanner from './HeroBanner.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe('HeroBanner', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('presents source-backed knowledge proof before the search action', () => {
    const wrapper = mount(HeroBanner, {
      global: { stubs: { RouterLink: true } },
    })

    const proof = wrapper.get('[data-testid="knowledge-proof"]')
    expect(proof.text()).toContain('来源化资料')
    expect(proof.text()).toContain('非遗项目')
    expect(proof.text()).toContain('权威来源类型')
  })

  it('keeps the editorial artwork as a stable, accessible hero asset', () => {
    const wrapper = mount(HeroBanner)

    const artwork = wrapper.get('[data-testid="hero-art-image"]')
    expect(artwork.attributes('src')).toBe('/editorial/hero-archive-textile-v1.png')
    expect(artwork.attributes('alt')).toContain('靛染线轴')
  })
})
