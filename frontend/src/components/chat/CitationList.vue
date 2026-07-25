<script setup lang="ts">
import type { Citation } from '@/types'

defineProps<{
  citations: Citation[]
}>()
</script>

<template>
  <div class="mt-2">
    <details class="text-sm">
      <summary class="text-[var(--text2)] cursor-pointer hover:text-[var(--accent)] transition-colors">
        📎 引用 ({{ citations.length }})
      </summary>
      <ul class="mt-2 space-y-1 pl-4">
        <li v-for="(c, i) in citations" :key="i" class="text-[var(--text3)] italic">
          {{ c.title }}
        </li>
      </ul>
    </details>
  </div>
</template>
