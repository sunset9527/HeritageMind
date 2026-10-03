// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import CraftDetailView from './CraftDetailView.vue'
import { getCraft } from '@/api/platform'

const route = reactive({ params: { slug: '蓝染' } })

vi.mock('vue-router', () => ({ useRoute: () => route }))
vi.mock('@/api/platform', () => ({ getCraft: vi.fn() }))

describe('CraftDetailView route changes', () => {
  it('reloads the craft when the active slug changes', async () => {
    vi.mocked(getCraft).mockImplementation(async (slug: string) => ({
      name: slug,
      slug,
      summary: `${slug}摘要`,
      content: `${slug}正文`,
      image: { url: null, status: 'unavailable' },
    }))

    const wrapper = mount(CraftDetailView)
    await flushPromises()
    route.params.slug = '剪纸'
    await flushPromises()

    expect(getCraft).toHaveBeenLastCalledWith('剪纸', expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(wrapper.text()).toContain('剪纸正文')
  })
})
