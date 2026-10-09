// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import InheritorDetailView from './InheritorDetailView.vue'
import { getInheritor } from '@/api/platform'

vi.mock('vue-router', () => ({ useRoute: () => ({ params: { slug: '尹昌武' } }) }))
vi.mock('@/api/platform', () => ({ getInheritor: vi.fn() }))

describe('InheritorDetailView', () => {
  it('shows the biography without rendering a book-source section', async () => {
    vi.mocked(getInheritor).mockResolvedValue({
      name: '尹昌武',
      slug: '尹昌武',
      craft_name: '自贡井盐深钻汲制技艺',
      region: '四川',
      recognition: '',
      biography: '尹昌武长期从事井盐深钻汲制技艺。',
      lineage: '',
      representative_works: '',
      sources: [{ name: '传承人大典', url: '', evidence: '重复的生平文字' }],
    })

    const wrapper = mount(InheritorDetailView)
    await flushPromises()

    expect(wrapper.text()).toContain('尹昌武长期从事井盐深钻汲制技艺。')
    expect(wrapper.text()).not.toContain('图书来源')
    expect(wrapper.text()).not.toContain('重复的生平文字')
    expect(wrapper.get('.inheritor-copy').classes()).toContain('inheritor-copy')
  })
})
