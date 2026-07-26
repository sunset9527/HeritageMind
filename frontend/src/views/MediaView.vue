<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { uploadMedia, listMedia, deleteMedia, type MediaItem } from '@/api/media'
import { getCrafts } from '@/api/meta'
import type { CraftItem } from '@/types'
import { ElMessage } from 'element-plus'

const crafts = ref<CraftItem[]>([])
const mediaItems = ref<MediaItem[]>([])
const uploading = ref(false)
const selectedCraft = ref('')
const filterType = ref('')

const form = ref({ craft_name: '', media_type: 'image', title: '' })

onMounted(async () => {
  try { crafts.value = await getCrafts() } catch { /* */ }
  await loadMedia()
})

async function loadMedia() {
  try {
    const resp = await listMedia(filterType.value || undefined, filterType.value || undefined)
    mediaItems.value = resp.items
  } catch { /* */ }
}

async function handleUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !form.value.craft_name) return
  uploading.value = true
  try {
    await uploadMedia(file, form.value.craft_name, form.value.media_type, form.value.title)
    ElMessage.success('上传成功')
    await loadMedia()
  } catch { ElMessage.error('上传失败') }
  finally { uploading.value = false; input.value = '' }
}

async function handleDelete(id: number) {
  try {
    await deleteMedia(id)
    ElMessage.success('已删除')
    await loadMedia()
  } catch { ElMessage.error('删除失败') }
}

function formatSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-6 py-6">
    <h2 class="headline mb-1">多媒体管理</h2>
    <p class="body text-[14px] mb-6">上传图片和音频，丰富非遗知识库</p>

    <!-- Upload -->
    <div class="setting-section">
      <h3>📤 上传文件</h3>
      <div class="flex flex-wrap gap-3 items-end">
        <div>
          <label class="text-xs text-[var(--text-tertiary)] block mb-1">技艺</label>
          <select v-model="form.craft_name" class="text-sm border rounded-lg px-3 py-2 bg-white">
            <option value="">选择技艺</option>
            <option v-for="c in crafts" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-[var(--text-tertiary)] block mb-1">类型</label>
          <select v-model="form.media_type" class="text-sm border rounded-lg px-3 py-2 bg-white">
            <option value="image">图片</option>
            <option value="audio">音频</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-[var(--text-tertiary)] block mb-1">标题</label>
          <input v-model="form.title" placeholder="文件描述" class="text-sm border rounded-lg px-3 py-2 bg-white w-40" />
        </div>
        <label class="px-5 py-2 rounded-full text-sm font-semibold cursor-pointer transition-colors"
               :class="form.craft_name ? 'bg-[var(--text)] text-white hover:opacity-90' : 'bg-gray-200 text-gray-400 cursor-not-allowed'">
          {{ uploading ? '上传中...' : '选择文件' }}
          <input type="file" :accept="form.media_type === 'image' ? 'image/*' : 'audio/*'"
                 class="hidden" @change="handleUpload" :disabled="!form.craft_name || uploading" />
        </label>
      </div>
    </div>

    <!-- Gallery -->
    <div class="setting-section">
      <div class="flex items-center justify-between mb-4">
        <h3>🖼️ 媒体库 ({{ mediaItems.length }})</h3>
        <div class="flex gap-2">
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
          <div v-else class="h-32 bg-gray-100 flex items-center justify-center text-3xl">🎵</div>
          <!-- Info -->
          <div class="p-2">
            <div class="text-xs font-medium truncate">{{ item.title || item.original_name }}</div>
            <div class="text-[11px] text-[var(--text-tertiary)]">{{ item.craft_name }} · {{ formatSize(item.size) }}</div>
          </div>
          <!-- Delete -->
          <button @click="handleDelete(item.id)"
                  class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/50 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity border-0 cursor-pointer">
            ✕
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
