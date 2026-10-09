// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppFooter from './AppFooter.vue'

describe('AppFooter', () => {
  it('states the project mission without listing implementation technologies', () => {
    const text = mount(AppFooter).text()

    expect(text).toContain('让每一门非遗，在可信的数字世界里被看见、被理解、被传承。')
    expect(text).not.toContain('LangGraph')
    expect(text).not.toContain('DeepSeek')
  })
})
