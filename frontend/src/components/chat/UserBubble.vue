<script setup lang="ts">
defineProps<{
  content: string
  timestamp?: string
}>()
</script>

<template>
  <div class="user-bubble">
    {{ content }}
  </div>
</template>
