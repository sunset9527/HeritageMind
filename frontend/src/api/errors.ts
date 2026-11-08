export interface ApiErrorInfo {
  message: string
  requestId?: string
}

type ErrorEnvelope = {
  error?: {
    message?: unknown
    request_id?: unknown
  }
  detail?: unknown
}

export function parseApiError(payload: unknown, fallback = '请求失败'): ApiErrorInfo {
  if (!payload || typeof payload !== 'object') return { message: fallback, requestId: undefined }

  const body = payload as ErrorEnvelope
  const message = body.error?.message
  if (typeof message === 'string' && message.trim()) {
    const requestId = body.error?.request_id
    return { message, requestId: typeof requestId === 'string' ? requestId : undefined }
  }

  if (typeof body.detail === 'string' && body.detail.trim()) {
    return { message: body.detail, requestId: undefined }
  }
  return { message: fallback, requestId: undefined }
}

export function formatApiError(error: ApiErrorInfo): string {
  return error.requestId ? `${error.message}（请求 ID: ${error.requestId}）` : error.message
}
