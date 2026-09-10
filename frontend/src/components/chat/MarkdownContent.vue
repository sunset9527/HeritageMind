<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const props = defineProps<{
  content: string
}>()

const md = new MarkdownIt({
  html: false,     // 禁原始 HTML（LLM 输出不可信）
  linkify: true,   // 自动识别 URL
  breaks: true,    // 单换行转 <br>（LLM 常用换行分段）
})

const rendered = computed(() => {
  if (!props.content) return ''
  return DOMPurify.sanitize(md.render(props.content))
})
</script>

<template>
  <div class="md-content" v-html="rendered"></div>
</template>

<style scoped>
.md-content {
  line-height: 1.7;
}
.md-content :deep(p) {
  margin: 0.5em 0;
}
.md-content :deep(p:first-child) {
  margin-top: 0;
}
.md-content :deep(p:last-child) {
  margin-bottom: 0;
}
.md-content :deep(strong) {
  font-weight: 600;
}
.md-content :deep(blockquote) {
  border-left: 3px solid var(--border-color, #ddd);
  margin: 0.5em 0;
  padding-left: 0.8em;
  color: var(--text-secondary, #666);
}
.md-content :deep(ol),
.md-content :deep(ul) {
  padding-left: 1.4em;
  margin: 0.5em 0;
}
.md-content :deep(li) {
  margin: 0.25em 0;
}
.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3) {
  margin: 0.8em 0 0.4em;
  font-weight: 600;
}
.md-content :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-size: 0.92em;
}
.md-content :deep(pre) {
  background: rgba(0, 0, 0, 0.06);
  padding: 0.8em 1em;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5em 0;
}
.md-content :deep(a) {
  color: var(--accent, #4a90d9);
  text-decoration: underline;
}
.md-content :deep(table) {
  border-collapse: collapse;
  margin: 0.5em 0;
}
.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid var(--border-color, #ddd);
  padding: 0.3em 0.6em;
}
</style>