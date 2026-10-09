// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
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

  it('uses dark, low-contrast surfaces for the debate panel and composer', () => {
    const wrapper = mount(ChatView, {
      global: {
        stubs: {
          RouterLink: true, UserBubble: true, AgentCard: true, GapNotice: true,
          DebateTimeline: true, CitationList: true, MarkdownContent: true,
          WorkflowTrace: true, RealtimeWorkflowDag: true, AnswerFeedback: true,
        },
      },
    })

    expect(wrapper.get('[data-testid="debate-panel"]').attributes('style')).toContain('rgba(41, 48, 37, 0.55)')
    expect(wrapper.get('[data-testid="chat-composer"]').attributes('style')).toContain('rgba(28, 32, 22, 0.92)')
  })

  it('offers questions from the loaded books crafts instead of legacy hard-coded examples', async () => {
    const meta = await import('@/api/meta')
    vi.mocked(meta.getCrafts).mockResolvedValue([{ id: 'books:miao', name: '苗族古歌' }])
    const wrapper = mount(ChatView, {
      global: { stubs: { RouterLink: true, UserBubble: true, AgentCard: true, GapNotice: true, DebateTimeline: true, CitationList: true, MarkdownContent: true, WorkflowTrace: true, RealtimeWorkflowDag: true, AnswerFeedback: true } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('苗族古歌')
    expect(wrapper.text()).not.toContain('景泰蓝的制作流程是什么？')
  })

  it('uses a searchable in-page craft picker instead of the native 1476-item select menu', async () => {
    const wrapper = mount(ChatView, {
      global: { stubs: { RouterLink: true, UserBubble: true, AgentCard: true, GapNotice: true, DebateTimeline: true, CitationList: true, MarkdownContent: true, WorkflowTrace: true, RealtimeWorkflowDag: true, AnswerFeedback: true } },
    })
    await flushPromises()
    await wrapper.get('.chat-toolbar button').trigger('click')

    const picker = wrapper.get('[data-testid="craft-picker"]')
    expect(picker.find('select').exists()).toBe(false)
    await picker.get('button').trigger('click')
    expect(picker.get('input').attributes('placeholder')).toContain('搜索技艺')
  })
})
