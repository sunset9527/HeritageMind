<script setup lang="ts">
import { onMounted, ref } from 'vue'
import HeroBanner from '@/components/dashboard/HeroBanner.vue'
import CraftCarousel from '@/components/dashboard/CraftCarousel.vue'
import FeatureCards from '@/components/dashboard/FeatureCards.vue'
import StatsBar from '@/components/dashboard/StatsBar.vue'
import { getDashboardSummary, type DashboardSummary } from '@/api/dashboard'

const summary = ref<DashboardSummary>()

onMounted(async () => {
  try { summary.value = await getDashboardSummary() } catch { /* The child components show honest placeholders. */ }
})
</script>

<template>
  <div class="dashboard-page">
    <HeroBanner :summary="summary" />
    <StatsBar :summary="summary" />
    <CraftCarousel />
    <FeatureCards />
  </div>
</template>

<style>
.dashboard-page { overflow: hidden; }
</style>
