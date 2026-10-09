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

  it('presents the dashboard summary supplied by its parent', () => {
    const wrapper = mount(HeroBanner, {
      props: { summary: { source_books: 10, document_count: 7688, total_characters: 1234567, project_count: 1143, inheritor_count: 44 } },
      global: { stubs: { RouterLink: true } },
    })

    const proof = wrapper.get('[data-testid="knowledge-proof"]')
    expect(proof.text()).toContain('7688')
    expect(proof.text()).toContain('1143')
    expect(proof.text()).toContain('123 万字')
    expect(proof.text()).toContain('已加载知识片段')
    expect(proof.text()).toContain('非遗项目')
    expect(proof.text()).toContain('可检索文本量')
  })

  it('keeps the editorial artwork as a stable, accessible hero asset', () => {
    const wrapper = mount(HeroBanner)

    expect(wrapper.get('section').attributes('data-scene')).toBe('indigo')
    const artwork = wrapper.get('[data-testid="hero-art-image"]')
    expect(artwork.attributes('src')).toBe('/editorial/hero-archive-textile-v1.png')
    expect(artwork.attributes('alt')).toContain('靛染线轴')
  })
})
