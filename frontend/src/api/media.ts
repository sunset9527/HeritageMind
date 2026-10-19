import client from './client'

export type MediaStatus = 'draft' | 'reviewed' | 'published'

export interface MediaItem {
  id: number
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

export async function uploadMedia(file: File, craftName: string, mediaType: string, title: string): Promise<MediaItem> {
  const form = new FormData()
  form.append('file', file)
  form.append('craft_name', craftName)
  form.append('media_type', mediaType)
  form.append('title', title || file.name)
  const { data } = await client.post<MediaItem>('/media/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
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
