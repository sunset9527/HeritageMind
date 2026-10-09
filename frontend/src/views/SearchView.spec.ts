// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchView from './SearchView.vue'

describe('SearchView', () => {
  it('uses a neutral search page title', () => {
    const wrapper = mount(SearchView)

    expect(wrapper.get('h1').text()).toBe('搜索')
    expect(wrapper.text()).not.toContain('AI 搜索')
  })
})
