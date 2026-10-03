// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CraftCarousel from './CraftCarousel.vue'
import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
import { listEncyclopedia } from '@/api/platform'

vi.mock('@/api/platform', () => ({ listEncyclopedia: vi.fn() }))

describe('CraftCarousel', () => {
  it('uses the shared image component for an API-backed craft image', async () => {
    vi.mocked(listEncyclopedia).mockResolvedValue([{
      name: '土家族民间故事',
      slug: '土家族民间故事',
      summary: '第一批国家级非遗名录记录',
      image: { url: null, status: 'unavailable' },
    }])

    const wrapper = mount(CraftCarousel, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    expect(wrapper.getComponent(EncyclopediaImage).props('image')).toEqual({
      url: null,
      status: 'unavailable',
    })
  })
})
