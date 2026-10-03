// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChatView from './ChatView.vue'

vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), warning: vi.fn() } }))
vi.mock('@/api/meta', () => ({
  getCrafts: vi.fn().mockResolvedValue([]),
  getProfiles: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/chat', () => ({ getSessions: vi.fn().mockResolvedValue({ items: [] }) }))

describe('ChatView editorial scene', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('places the research workspace in the indigo editorial scene', () => {
    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          RouterLink: true,
          UserBubble: true,
          AgentCard: true,
          GapNotice: true,
          DebateTimeline: true,
          CitationList: true,
          MarkdownContent: true,
          WorkflowTrace: true,
          RealtimeWorkflowDag: true,
          AnswerFeedback: true,
        },
      },
    })

    expect(wrapper.find('[data-scene="indigo"]').exists()).toBe(true)
  })
})
