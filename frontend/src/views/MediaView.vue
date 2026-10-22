<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import {
  uploadMedia,
  listMedia,
  listAdminMedia,
  deleteMedia,
  updateMediaStatus,
  getMediaErrorMessage,
  type MediaItem,
  type MediaStatus,
} from '@/api/media'
import { getCrafts } from '@/api/meta'
import { useAuthStore } from '@/stores/auth'
import type { CraftItem } from '@/types'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const crafts = ref<CraftItem[]>([])
const mediaItems = ref<MediaItem[]>([])
const uploading = ref(false)
const uploadError = ref('')
const selectedCraft = ref('')
const filterType = ref('')
const isAdmin = computed(() => auth.user?.role === 'admin')

const form = ref({ craft_id: '', media_type: 'image' as 'image' | 'audio', title: '' })
const selectedUploadCraft = computed(() => crafts.value.find(craft => craft.id === form.value.craft_id))
const acceptedFormats = computed(() => form.value.media_type === 'image'
  ? '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp'
  : '.mp3,.wav,.m4a,.flac,.ogg,audio/mpeg,audio/wav,audio/mp4,audio/flac,audio/ogg')

onMounted(async () => {
  try { crafts.value = await getCrafts() } catch { /* */ }
  await loadMedia()
})

async function loadMedia() {
  try {
    const listFn = isAdmin.value ? listAdminMedia : listMedia
    const resp = await listFn(selectedCraft.value || undefined, filterType.value || undefined)
    mediaItems.value = resp.items
  } catch { /* */ }
}

async function handleUpload(e: Event) {
  if (!isAdmin.value) return
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  const craft = selectedUploadCraft.value
  if (!file || !craft) return
  const maxBytes = form.value.media_type === 'image' ? 10 * 1024 * 1024 : 50 * 1024 * 1024
  if (file.size > maxBytes) {
    uploadError.value = form.value.media_type === 'image' ? '图片最大 10 MiB' : '音频最大 50 MiB'
    ElMessage.error(uploadError.value)
    input.value = ''
    return
  }
  uploading.value = true
  uploadError.value = ''
  try {
    await uploadMedia(file, craft, form.value.media_type, form.value.title)
    ElMessage.success('上传成功')
    await loadMedia()
  } catch (error) {
    uploadError.value = getMediaErrorMessage(error)
    ElMessage.error(uploadError.value)
  }
  finally { uploading.value = false; input.value = '' }
}

async function handleDelete(id: number) {
  if (!isAdmin.value) return
  try {
    await deleteMedia(id)
    ElMessage.success('已删除')
    await loadMedia()
  } catch { ElMessage.error('删除失败') }
}

async function handleStatusChange(item: MediaItem, event: Event) {
  if (!isAdmin.value) return
  const status = (event.target as HTMLSelectElement).value as MediaStatus
  const previous = item.status
  item.status = status
  try {
    await updateMediaStatus(item.id, status)
    ElMessage.success('状态已更新')
  } catch {
    item.status = previous
    ElMessage.error('状态更新失败')
  }
}

function formatSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div class="heritage-page max-w-5xl mx-auto px-6 py-10">
    <p class="page-kicker">资料归档</p>
    <h1 class="page-title">{{ isAdmin ? '多媒体管理' : '多媒体资源' }}</h1>
    <p class="page-intro">{{ isAdmin ? '上传图片和音频，丰富非遗知识库' : '浏览已审核发布的非遗图片和音频' }}</p>

    <!-- Upload -->
    <div v-if="isAdmin" class="setting-section">
      <h3>上传文件</h3>
      <div class="flex flex-wrap gap-3 items-end">
        <div>
          <label for="media-craft" class="text-sm text-[var(--text-secondary)] block mb-1">技艺</label>
          <select id="media-craft" v-model="form.craft_id" class="text-base border rounded-lg px-3 min-h-11 bg-white">
            <option value="">选择技艺</option>
            <option v-for="c in crafts" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label for="media-type" class="text-sm text-[var(--text-secondary)] block mb-1">类型</label>
          <select id="media-type" v-model="form.media_type" class="text-base border rounded-lg px-3 min-h-11 bg-white">
            <option value="image">图片</option>
            <option value="audio">音频</option>
          </select>
        </div>
        <div>
          <label for="media-title" class="text-sm text-[var(--text-secondary)] block mb-1">标题</label>
          <input id="media-title" v-model="form.title" placeholder="文件描述" class="text-base border rounded-lg px-3 min-h-11 bg-white w-48" />
        </div>
        <label class="px-5 min-h-11 rounded-full text-sm font-semibold cursor-pointer transition-colors inline-flex items-center"
               :class="form.craft_id ? 'bg-[var(--accent)] text-[#1c2016] hover:opacity-90' : 'bg-gray-200 text-gray-500 cursor-not-allowed'">
          {{ uploading ? '上传中...' : '选择文件' }}
          <input type="file" :accept="acceptedFormats"
                 class="sr-only" @change="handleUpload" :disabled="!form.craft_id || uploading" />
        </label>
      </div>
      <p class="mt-3 text-sm text-[var(--text-secondary)]">
        {{ form.media_type === 'image' ? '图片最大 10 MiB，支持 JPG、PNG、WebP' : '音频最大 50 MiB，时长不超过 30 分钟，支持 MP3、WAV、M4A、FLAC、OGG' }}
      </p>
      <p v-if="uploadError" class="mt-2 text-sm text-red-700" role="alert" aria-live="polite">{{ uploadError }}</p>
    </div>

    <!-- Gallery -->
    <div class="setting-section">
      <div class="flex items-center justify-between mb-4">
        <h3>媒体库 ({{ mediaItems.length }})</h3>
        <div class="flex gap-2">
          <select v-model="selectedCraft" @change="loadMedia" class="text-xs border rounded-lg px-2 py-1.5 bg-white">
            <option value="">全部技艺</option>
            <option v-for="c in crafts" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
          <select v-model="filterType" @change="loadMedia" class="text-xs border rounded-lg px-2 py-1.5 bg-white">
            <option value="">全部</option>
            <option value="image">图片</option>
            <option value="audio">音频</option>
          </select>
        </div>
      </div>
      <div v-if="mediaItems.length === 0" class="text-sm text-[var(--text-tertiary)] text-center py-8">
        暂无媒体文件，上传一张试试
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div v-for="item in mediaItems" :key="item.id"
             class="rounded-xl overflow-hidden border border-[var(--border)] bg-white relative group">
          <!-- Image preview -->
          <div v-if="item.media_type === 'image'" class="h-32 bg-gray-100">
            <img :src="item.url" :alt="item.title" class="w-full h-full object-cover" />
          </div>
          <!-- Audio placeholder -->
          <div v-else class="h-32 bg-gray-100 flex items-center justify-center" aria-label="音频文件">
            <svg viewBox="0 0 24 24" class="w-8 h-8 text-[var(--text-secondary)]" aria-hidden="true">
              <path fill="currentColor" d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6Z" />
            </svg>
          </div>
          <!-- Info -->
          <div class="p-2">
            <div class="text-xs font-medium truncate">{{ item.title || item.original_name }}</div>
            <div class="text-[11px] text-[var(--text-tertiary)]">{{ item.craft_name }} · {{ formatSize(item.size) }}</div>
            <select v-if="isAdmin" :value="item.status" @change="handleStatusChange(item, $event)"
                    class="mt-1 w-full text-[11px] border rounded px-1 py-0.5 bg-white">
              <option value="draft">草稿</option>
              <option value="reviewed">已审核</option>
              <option value="published">已发布</option>
            </select>
          </div>
          <!-- Delete -->
          <button v-if="isAdmin" @click="handleDelete(item.id)"
                  :aria-label="`删除 ${item.title || item.original_name}`"
                  class="absolute top-1 right-1 w-11 h-11 rounded-full bg-black/70 text-white text-sm flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity border-0 cursor-pointer">
            ✕
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
