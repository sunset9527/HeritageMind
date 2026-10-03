<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import EditorialPageShell from '@/components/layout/EditorialPageShell.vue'
import type { EditorialScene } from '@/components/layout/editorial-scenes'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
const route = useRoute()

const routeScenes: Record<string, EditorialScene> = {
  search: 'indigo',
  encyclopedia: 'ink',
  'craft-detail': 'ink',
  inheritors: 'bamboo',
  'inheritor-detail': 'bamboo',
  graph: 'bamboo',
  media: 'clay',
  profile: 'clay',
  settings: 'clay',
  login: 'clay',
  register: 'clay',
  'not-found': 'ink',
}

const routeScene = computed(() => routeScenes[String(route.name)])

onMounted(() => {
  settings.loadServerConfig()
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[var(--bg)]">
    <AppHeader />
    <main class="flex-1">
      <RouterView v-slot="{ Component }">
        <EditorialPageShell v-if="routeScene" :scene="routeScene">
          <component :is="Component" />
        </EditorialPageShell>
        <component :is="Component" v-else />
      </RouterView>
    </main>
    <AppFooter />
  </div>
</template>
