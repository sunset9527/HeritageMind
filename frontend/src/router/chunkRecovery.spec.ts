// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

const router = {
  beforeEach: vi.fn(),
  afterEach: vi.fn(),
  onError: vi.fn(),
}

vi.mock('vue-router', () => ({
  createRouter: () => router,
  createWebHistory: () => ({}),
}))

describe('router stale chunk recovery', () => {
  beforeEach(() => {
    vi.resetModules()
    router.beforeEach.mockClear()
    router.afterEach.mockClear()
    router.onError.mockClear()
    sessionStorage.clear()
  })

  it('marks a failed lazy-loaded page for one recovery reload', async () => {
    const { createChunkRecoveryHandler } = await import('./index')

    expect(router.onError).toHaveBeenCalledTimes(1)
    const reload = vi.fn()
    const handler = createChunkRecoveryHandler(reload)
    handler(new Error('Failed to fetch dynamically imported module'))

    expect(sessionStorage.getItem('heritagemind:chunk-recovery')).toBe('attempted')
    expect(reload).toHaveBeenCalledTimes(1)
  })
})
