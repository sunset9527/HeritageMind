// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import HeroBanner from './HeroBanner.vue'
import { getCrafts, getDocumentSummary } from '@/api/meta'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/meta', () => ({
  getCrafts: vi.fn(),
  getDocumentSummary: vi.fn(),
}))

describe('HeroBanner', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getCrafts).mockResolvedValue(Array.from({ length: 23 }, (_, index) => ({
      id: `craft-${index}`,
      name: `技艺 ${index}`,
    })))
    vi.mocked(getDocumentSummary).mockResolvedValue({ total_documents: 46 })
  })

  it('presents API-backed knowledge proof before the search action', async () => {
    const wrapper = mount(HeroBanner, {
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()

    const proof = wrapper.get('[data-testid="knowledge-proof"]')
    expect(proof.text()).toContain('46')
    expect(proof.text()).toContain('23')
    expect(proof.text()).toContain('可核查')
    expect(proof.text()).toContain('已加载文档')
    expect(proof.text()).toContain('非遗项目')
  })

  it('keeps the editorial artwork as a stable, accessible hero asset', () => {
    const wrapper = mount(HeroBanner)

    const artwork = wrapper.get('[data-testid="hero-art-image"]')
    expect(artwork.attributes('src')).toBe('/editorial/hero-archive-textile-v1.png')
    expect(artwork.attributes('alt')).toContain('靛染线轴')
  })
})
