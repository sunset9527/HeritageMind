<script setup lang="ts">
import { computed, ref } from 'vue'

type ImageStatus = 'verified' | 'legacy_local' | 'pending_review' | 'extracted' | 'unavailable'

const props = defineProps<{
  name: string
  image: { url: string | null; status: ImageStatus }
}>()

const failed = ref(false)
const showImage = computed(() => Boolean(props.image.url) && !failed.value)

function markFailed() {
  failed.value = true
}
</script>

<template>
  <div class="encyclopedia-image">
    <img
      v-if="showImage"
      :src="image.url!"
      :alt="name"
      @error="markFailed"
    />
    <div
      v-else
      class="fallback"
      data-testid="encyclopedia-image-fallback"
      :aria-label="`${name}待补充图像`"
      role="img"
    >
      <span>待补充图像</span>
    </div>
  </div>
</template>

<style scoped>
.encyclopedia-image{width:100%;height:100%;min-height:160px;overflow:hidden;background:#253021}.encyclopedia-image img{display:block;width:100%;height:100%;object-fit:cover;filter:saturate(.76) contrast(.95)}.fallback{display:grid;width:100%;height:100%;min-height:inherit;place-items:center;background:radial-gradient(circle at 67% 34%,rgba(213,183,126,.32) 0 7%,transparent 7.5%),linear-gradient(135deg,#1e281d,#4b5942);color:#f1e7d2;font-family:var(--font-brush);font-size:1.5rem;letter-spacing:.16em}.fallback span{padding:.45rem .7rem;border:1px solid rgba(241,231,210,.42)}
</style>
