<script setup lang="ts">
import HeroBanner from '@/components/dashboard/HeroBanner.vue'
import CraftCarousel from '@/components/dashboard/CraftCarousel.vue'
import FeatureCards from '@/components/dashboard/FeatureCards.vue'
</script>

<template>
  <div class="dashboard-page">
    <HeroBanner />
    <CraftCarousel />
    <FeatureCards />
  </div>
</template>

<style>
.dashboard-page {
  font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.dashboard-page .stat-num,
.dashboard-page [class*="tracking-wider"] {
  font-family: 'Ma Shan Zheng', 'STKaiti', 'KaiTi', serif;
}
</style>
