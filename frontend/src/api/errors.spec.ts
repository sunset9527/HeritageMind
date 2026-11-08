import { describe, expect, it } from 'vitest'

import { formatApiError, parseApiError } from './errors'


describe('parseApiError', () => {
  it('prefers the stable error envelope and retains its request id', () => {
    expect(parseApiError({
      error: {
        code: 'dependency_unavailable',
        message: '当前服务暂不可用，请稍后重试',
        request_id: 'trace-42',
      },
    })).toEqual({
      message: '当前服务暂不可用，请稍后重试',
      requestId: 'trace-42',
    })
  })

  it('keeps legacy detail responses usable during API rollout', () => {
    expect(parseApiError({ detail: '旧接口错误说明' })).toEqual({
      message: '旧接口错误说明',
      requestId: undefined,
    })
  })

  it('uses a caller fallback for an unknown response body', () => {
    expect(parseApiError({}, '网络请求失败')).toEqual({
      message: '网络请求失败',
      requestId: undefined,
    })
  })

  it('shows the request id with an otherwise stable public message', () => {
    expect(formatApiError({ message: '请求过于频繁，请稍后再试', requestId: 'trace-42' }))
      .toBe('请求过于频繁，请稍后再试（请求 ID: trace-42）')
  })
})
