// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { loginMock, registerMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  registerMock: vi.fn(),
}))

vi.mock('@/api/auth', () => ({
  login: loginMock,
  register: registerMock,
  getMe: vi.fn(),
}))

import { useAuthStore } from './auth'


describe('authentication error display', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    loginMock.mockReset()
    registerMock.mockReset()
    localStorage.clear()
  })

  it('shows the stable backend login message and request id', async () => {
    loginMock.mockRejectedValue({
      response: {
        data: {
          error: {
            code: 'unauthenticated',
            message: '请先登录后再试',
            request_id: 'trace-login-42',
          },
        },
      },
    })
    const store = useAuthStore()

    await expect(store.login('demo', 'not-a-real-password')).rejects
      .toThrow('请先登录后再试（请求 ID: trace-login-42）')
    expect(store.error).toBe('请先登录后再试（请求 ID: trace-login-42）')
  })
})
