// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CraftDetailView from './CraftDetailView.vue'
import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
import { getCraft } from '@/api/platform'

vi.mock('vue-router', () => ({ useRoute: () => ({ params: { slug: '土家族民间故事' } }) }))
vi.mock('@/api/platform', () => ({ getCraft: vi.fn() }))

describe('CraftDetailView', () => {
  it('renders the shared image component from the entry image record', async () => {
    vi.mocked(getCraft).mockResolvedValue({
      name: '土家族民间故事',
      slug: '土家族民间故事',
      summary: '第一批国家级非遗名录记录',
      content: '正文',
      image: { url: null, status: 'unavailable' },
    })

    const wrapper = mount(CraftDetailView)
    await flushPromises()

    expect(wrapper.getComponent(EncyclopediaImage).props('image')).toEqual({ url: null, status: 'unavailable' })
  })

  it('renders full detail content once without repeating the card summary', async () => {
    vi.mocked(getCraft).mockResolvedValue({
      name: '苗族古歌',
      slug: '苗族古歌',
      summary: '用于列表的简短摘要。',
      content: '来自书籍的完整正文。',
      image: { url: '/local-books/images/craft', status: 'extracted' },
    })

    const wrapper = mount(CraftDetailView)
    await flushPromises()

    expect(wrapper.text()).toContain('来自书籍的完整正文。')
    expect(wrapper.text()).not.toContain('用于列表的简短摘要。')
    expect(wrapper.get('.detail-copy').classes()).toContain('detail-copy')
  })
})
