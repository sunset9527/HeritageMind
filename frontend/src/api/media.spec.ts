import { beforeEach, describe, expect, it, vi } from 'vitest'

const { post } = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('./client', () => ({ default: { post } }))

import { getMediaErrorMessage, uploadMedia } from './media'


describe('media upload contract', () => {
  beforeEach(() => post.mockReset())

  it('sends matching craft_id and craft_name from the selected craft object', async () => {
    post.mockResolvedValue({ data: { id: 1 } })
    const file = new File(['image'], 'photo.png', { type: 'image/png' })

    await uploadMedia(file, { id: 'jingtailan', name: '景泰蓝' }, 'image', '')

    const form = post.mock.calls[0][1] as FormData
    expect(form.get('craft_id')).toBe('jingtailan')
    expect(form.get('craft_name')).toBe('景泰蓝')
    expect(form.get('media_type')).toBe('image')
  })

  it('surfaces backend detail with a useful fallback', () => {
    expect(getMediaErrorMessage({ response: { data: { detail: '图片无法解码' } } })).toBe('图片无法解码')
    expect(getMediaErrorMessage(new Error('network down'))).toBe('network down')
    expect(getMediaErrorMessage({})).toBe('上传失败，请检查文件格式和大小后重试')
  })
})
