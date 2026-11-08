// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'
import client from './client'


describe('public API client', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('uses the Vite same-origin API proxy during development', () => {
    expect(client.defaults.baseURL).toBe('/api')
  })

  it('reads a user API key from sessionStorage without persisting it', async () => {
    sessionStorage.setItem('hm_user_api_key', 'session-secret')

    const handlers = (client.interceptors.request as any).handlers
    const config = await handlers[0].fulfilled({ headers: {} })

    expect(config.headers['X-API-Key']).toBe('session-secret')
    expect(localStorage.getItem('hm_user_api_key')).toBeNull()
  })
})
