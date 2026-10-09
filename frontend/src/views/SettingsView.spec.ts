import { describe, expect, it } from 'vitest'
import source from './SettingsView.vue?raw'

describe('SettingsView', () => {
  it('uses a dark background for the API key notice', () => {
    expect(source).toContain('background: #293025')
    expect(source).not.toContain('background: #fafafa')
  })

  it('keeps unselected provider buttons readable on the dark page', () => {
    expect(source).toContain("bg-[var(--surface)] text-[var(--text-secondary)]")
    expect(source).not.toContain('bg-gray-100 text-[var(--text2)]')
  })

  it('describes the project mission instead of its technical implementation', () => {
    expect(source).toContain('面向中国非遗的可信知识探索平台')
    expect(source).toContain('让传统在数字时代被看见、被理解、被传承')
    expect(source).toContain('来源可追溯、知识可核查')
    expect(source).not.toContain('架构</b>：FastAPI + LangGraph + Vue 3')
  })
})
