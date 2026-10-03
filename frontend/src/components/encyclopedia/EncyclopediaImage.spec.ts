// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EncyclopediaImage from './EncyclopediaImage.vue'

describe('EncyclopediaImage', () => {
  it('replaces a failed official image with an accessible fallback instead of a broken img', async () => {
    const wrapper = mount(EncyclopediaImage, {
      props: {
        name: '土家族民间故事',
        image: { url: 'https://museum.example/tujia.jpg', status: 'verified' },
      },
    })

    await wrapper.get('img').trigger('error')

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.get('[data-testid="encyclopedia-image-fallback"]').text()).toContain('待补充图像')
    expect(wrapper.get('[data-testid="encyclopedia-image-fallback"]').attributes('aria-label')).toContain('土家族民间故事')
  })
})
