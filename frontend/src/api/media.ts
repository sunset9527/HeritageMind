import client from './client'
import type { CraftItem } from '@/types'

export type MediaStatus = 'draft' | 'reviewed' | 'published'

export interface MediaItem {
  id: number
  craft_id?: string | null
  craft_name: string
  media_type: string
  filename: string
  original_name: string
  mime_type: string
  size: number
  title: string
  status: MediaStatus
  created_at: string
  url: string
}

export interface MediaListResponse {
  items: MediaItem[]
  total: number
}

export async function uploadMedia(file: File, craft: CraftItem, mediaType: string, title: string): Promise<MediaItem> {
  const form = new FormData()
  form.append('file', file)
  form.append('craft_id', craft.id)
  form.append('craft_name', craft.name)
  form.append('media_type', mediaType)
  form.append('title', title || file.name)
  const { data } = await client.post<MediaItem>('/media/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export function getMediaErrorMessage(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map(item => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : ''))
      .filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  if (error instanceof Error && error.message.trim()) return error.message
  return '上传失败，请检查文件格式和大小后重试'
}

export async function listMedia(craftName?: string, mediaType?: string): Promise<MediaListResponse> {
  const params: Record<string, string> = {}
  if (craftName) params.craft_name = craftName
  if (mediaType) params.media_type = mediaType
  const { data } = await client.get<MediaListResponse>('/media/list', { params })
  return data
}

export async function listAdminMedia(craftName?: string, mediaType?: string): Promise<MediaListResponse> {
  const params: Record<string, string> = {}
  if (craftName) params.craft_name = craftName
  if (mediaType) params.media_type = mediaType
  const { data } = await client.get<MediaListResponse>('/admin/media', { params })
  return data
}

export async function deleteMedia(id: number): Promise<void> {
  await client.delete(`/media/${id}`)
}

export async function updateMediaStatus(id: number, status: MediaStatus): Promise<void> {
  await client.put(`/media/${id}/status`, { status })
}
