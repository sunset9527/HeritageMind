// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import GraphView from './GraphView.vue'

vi.mock('@/api/graph', () => ({
  getStats: vi.fn().mockResolvedValue({ total_nodes: 1175, total_edges: 636, node_types: { craft: 1 } }),
  getVisualization: vi.fn().mockResolvedValue({ html: '<html></html>' }),
}))

describe('GraphView', () => {
  it('uses high-contrast text for metrics on the light statistic cards', async () => {
    const wrapper = mount(GraphView, { global: { plugins: [createPinia()] } })
    await flushPromises()

    expect(getComputedStyle(wrapper.get('.graph-stat').element).backgroundColor).toBe('rgb(41, 48, 37)')
    expect(wrapper.get('[data-testid="graph-node-count"]').attributes('style')).toContain('color: rgb(244, 240, 231)')
    expect(wrapper.get('[data-testid="graph-node-label"]').attributes('style')).toContain('color: rgb(211, 216, 204)')
  })
})
