import { describe, expect, it } from 'vitest'
import mediaApiSource from '@/api/media.ts?raw'
import viewSource from './MediaView.vue?raw'


describe('MediaView authorization UX', () => {
  it('uses the public list for visitors and the all-status list for admins', () => {
    expect(mediaApiSource).toContain("client.get<MediaListResponse>('/admin/media'")
    expect(viewSource).toContain('isAdmin.value ? listAdminMedia : listMedia')
  })

  it('passes the type filter only as media_type, never as craft_name', () => {
    expect(viewSource).toContain(
      'listFn(selectedCraft.value || undefined, filterType.value || undefined)',
    )
    expect(viewSource).not.toContain(
      'listMedia(filterType.value || undefined, filterType.value || undefined)',
    )
  })

  it('shows upload and delete controls only to administrators', () => {
    expect(viewSource).toContain("auth.user?.role === 'admin'")
    expect(viewSource.match(/v-if="isAdmin"/g)?.length).toBeGreaterThanOrEqual(2)
  })

  it('provides the minimal admin status review action', () => {
    expect(mediaApiSource).toContain('export async function updateMediaStatus')
    expect(mediaApiSource).toContain("client.put(`/media/${id}/status`, { status })")
    expect(viewSource).toContain('@change="handleStatusChange(item, $event)"')
  })

  it('uses exact upload formats and displays resource limits', () => {
    expect(viewSource).toContain('.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp')
    expect(viewSource).toContain('.mp3,.wav,.m4a,.flac,.ogg,audio/mpeg,audio/wav,audio/mp4,audio/flac,audio/ogg')
    expect(viewSource).toContain('图片最大 10 MiB')
    expect(viewSource).toContain('音频最大 50 MiB，时长不超过 30 分钟')
  })

  it('keeps the stable craft id and shows backend error detail', () => {
    expect(viewSource).toContain("form = ref({ craft_id: ''")
    expect(viewSource).toContain('getMediaErrorMessage(error)')
    expect(mediaApiSource).toContain("form.append('craft_id', craft.id)")
    expect(mediaApiSource).toContain("form.append('craft_name', craft.name)")
  })
})
