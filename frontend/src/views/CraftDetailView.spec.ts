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
})
