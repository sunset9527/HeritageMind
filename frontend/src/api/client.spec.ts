import { describe, expect, it } from 'vitest'
import client from './client'


describe('public API client', () => {
  it('uses the Vite same-origin API proxy during development', () => {
    expect(client.defaults.baseURL).toBe('/api')
  })
})
