<script setup lang="ts">
defineProps<{
  text: string
}>()
</script>

<template>
  <div class="gap-notice" v-if="text">
    ⚠️ <b>知识缺口</b>：{{ text }}
  </div>
</template>
