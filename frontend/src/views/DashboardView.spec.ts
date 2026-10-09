// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DashboardView from './DashboardView.vue'
import { getDashboardSummary } from '@/api/dashboard'

vi.mock('@/api/dashboard', () => ({ getDashboardSummary: vi.fn() }))

describe('DashboardView', () => {
  it('shares one API-backed summary with both dashboard statistic areas', async () => {
    vi.mocked(getDashboardSummary).mockResolvedValue({
      source_books: 2,
      document_count: 1,
      total_characters: 100,
      project_count: 2,
      inheritor_count: 1,
    })

    const wrapper = mount(DashboardView, {
      global: {
        stubs: {
          HeroBanner: { props: ['summary'], template: '<div data-testid="hero">{{ summary?.project_count }}</div>' },
          StatsBar: { props: ['summary'], template: '<div data-testid="stats">{{ summary?.document_count }} / {{ summary?.total_characters }}</div>' },
          CraftCarousel: true,
          FeatureCards: true,
        },
      },
    })
    await flushPromises()

    expect(getDashboardSummary).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="hero"]').text()).toBe('2')
    expect(wrapper.get('[data-testid="stats"]').text()).toBe('1 / 100')
  })
})
