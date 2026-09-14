<script setup lang="ts">
import HeroBanner from '@/components/dashboard/HeroBanner.vue'
import CraftCarousel from '@/components/dashboard/CraftCarousel.vue'
import FeatureCards from '@/components/dashboard/FeatureCards.vue'
import StatsBar from '@/components/dashboard/StatsBar.vue'
</script>

<template>
  <div class="dashboard-page">
    <HeroBanner />
    <StatsBar />
    <CraftCarousel />
    <FeatureCards />
  </div>
</template>

<style>
.dashboard-page { overflow: hidden; }
</style>
