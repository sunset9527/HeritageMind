// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EncyclopediaView from './EncyclopediaView.vue'
import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
import { listEncyclopedia } from '@/api/platform'

vi.mock('@/api/platform', () => ({ listEncyclopedia: vi.fn() }))

describe('EncyclopediaView', () => {
  it('uses the shared image component instead of constructing a static image path', async () => {
    vi.mocked(listEncyclopedia).mockResolvedValue([{
      name: '土家族民间故事',
      slug: '土家族民间故事',
      summary: '第一批国家级非遗名录记录',
      image: { url: null, status: 'unavailable' },
    }])

    const wrapper = mount(EncyclopediaView, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    const image = wrapper.getComponent(EncyclopediaImage)
    expect(image.props('image')).toEqual({ url: null, status: 'unavailable' })
    expect(wrapper.html()).not.toContain('/crafts/土家族民间故事.jpg')
  })
})
