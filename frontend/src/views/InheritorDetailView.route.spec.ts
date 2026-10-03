// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import InheritorDetailView from './InheritorDetailView.vue'
import { getInheritor } from '@/api/platform'

const route = reactive({ params: { slug: '传承人甲' } })

vi.mock('vue-router', () => ({ useRoute: () => route }))
vi.mock('@/api/platform', () => ({ getInheritor: vi.fn() }))

describe('InheritorDetailView route changes', () => {
  it('reloads the inheritor when the active slug changes', async () => {
    vi.mocked(getInheritor).mockImplementation(async (slug: string) => ({
      name: slug,
      slug,
      craft_name: '蓝染',
      region: '贵州',
      recognition: '',
      biography: `${slug}生平`,
      lineage: '',
      representative_works: '',
      sources: [],
    }))

    const wrapper = mount(InheritorDetailView)
    await flushPromises()
    route.params.slug = '传承人乙'
    await flushPromises()

    expect(getInheritor).toHaveBeenLastCalledWith('传承人乙', expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(wrapper.text()).toContain('传承人乙生平')
  })
})
