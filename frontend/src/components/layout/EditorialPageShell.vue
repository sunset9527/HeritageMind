<script setup lang="ts">
import { computed } from 'vue'
import { editorialScenes, type EditorialScene } from './editorial-scenes'

const props = withDefaults(defineProps<{
  scene: EditorialScene
  index?: string
  kicker?: string
  title?: string
  intro?: string
  readingSurface?: 'paper' | 'workbench'
}>(), {
  index: '',
  kicker: '',
  title: '',
  intro: '',
  readingSurface: 'workbench',
})

const artwork = computed(() => editorialScenes[props.scene])
</script>

<template>
  <section class="editorial-page-shell" :class="`surface-${readingSurface}`" :data-scene="scene">
    <div class="scene-glow" aria-hidden="true" />
    <img class="scene-artwork" :src="artwork.artwork" :alt="artwork.alt" />
    <header v-if="kicker || title || intro" class="scene-heading">
      <p v-if="index || kicker" class="scene-kicker"><span v-if="index">{{ index }}</span>{{ kicker }}</p>
      <h1 v-if="title">{{ title }}</h1>
      <p v-if="intro" class="scene-intro">{{ intro }}</p>
    </header>
    <div class="scene-content"><slot /></div>
  </section>
</template>

<style scoped>
.editorial-page-shell{isolation:isolate;position:relative;min-height:calc(100dvh - 52px);overflow:hidden;background:#1c2016;color:#f4f0e7}.scene-glow{position:absolute;inset:0;z-index:-3;background:radial-gradient(circle at 84% 5%,rgba(120,134,96,.62),transparent 32%),radial-gradient(circle at 36% 90%,rgba(70,82,49,.45),transparent 38%),#1c2016}.scene-artwork{position:absolute;z-index:-2;top:0;right:0;width:min(72rem,82vw);height:min(38rem,74vh);object-fit:cover;object-position:right top;opacity:.9;mix-blend-mode:normal;pointer-events:none}.scene-artwork::selection{background:transparent}.scene-heading{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:70px 40px 35px}.scene-kicker{display:flex;gap:14px;margin:0 0 15px;color:#d4b77e;font:600 .68rem 'Times New Roman',serif;letter-spacing:.2em}.scene-kicker span{color:#f4f0e7}.scene-heading h1{max-width:560px;margin:0;color:#f4f0e7;font-family:var(--font-brush);font-size:clamp(2.6rem,5vw,4.7rem);font-weight:400;letter-spacing:.1em;line-height:1.08}.scene-intro{max-width:470px;margin:18px 0 0;color:#d3d8cc;font-size:.95rem;line-height:1.8}.scene-content{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:0 40px 76px}.surface-paper .scene-content{background:linear-gradient(90deg,rgba(244,240,231,.96),rgba(244,240,231,.9));color:#25291f}@media(max-width:760px){.scene-artwork{width:100%;height:340px;opacity:.42}.scene-heading{padding:50px 22px 28px}.scene-content{padding:0 18px 48px}.scene-heading h1{font-size:clamp(2.35rem,11vw,3.6rem)}.surface-paper .scene-content{margin:0 18px;padding:24px 18px 48px}}
</style>
