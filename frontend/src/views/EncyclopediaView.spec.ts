// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EncyclopediaView from './EncyclopediaView.vue'
import EncyclopediaImage from '@/components/encyclopedia/EncyclopediaImage.vue'
import { listEncyclopedia } from '@/api/platform'

vi.mock('@/api/platform', () => ({ listEncyclopedia: vi.fn() }))

describe('EncyclopediaView', () => {
  beforeEach(() => vi.mocked(listEncyclopedia).mockReset())

  it('shows loading feedback until the initial page request resolves', async () => {
    let resolveRequest!: (entries: any[]) => void
    vi.mocked(listEncyclopedia).mockReturnValue(new Promise((resolve) => { resolveRequest = resolve }))

    const wrapper = mount(EncyclopediaView, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })

    expect(wrapper.text()).toContain('正在加载百科条目')
    resolveRequest([])
    await flushPromises()
    wrapper.unmount()
  })

  it('retries the page request after a failure', async () => {
    vi.mocked(listEncyclopedia)
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce([])

    const wrapper = mount(EncyclopediaView, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(listEncyclopedia).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('暂未发布百科条目')
  })

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
