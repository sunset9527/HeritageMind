<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { getCrafts } from '@/api/meta'
import type { CraftItem } from '@/types'

const router = useRouter()
const chat = useChatStore()

const allCrafts = ref<CraftItem[]>([])
const current = ref(0)
const fading = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

// 百度图片 — 23 张，按技艺顺序精确匹配，找不到的用同类工艺图片
// 技艺名与图片关键词对应关系见注释
const IMAGES: Record<string, string> = {
  // === 精确匹配（百度搜索关键词命中）===
  '景泰蓝':   'https://img2.baidu.com/it/u=1466243676,646478485&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=1194',
  '苏绣':     'https://img2.baidu.com/it/u=1946916348,985762512&fm=253&app=138&f=JPEG?w=800&h=1173',
  '龙泉青瓷': 'https://img0.baidu.com/it/u=323105455,1423536465&fm=253&app=138&f=JPEG?w=800&h=600',
  '剪纸':     'https://img0.baidu.com/it/u=1925368144,3473524428&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=600',
  '景德镇瓷器':'https://img0.baidu.com/it/u=2454072607,3145129901&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=600',
  '皮影戏':   'https://img0.baidu.com/it/u=3957963608,2916761311&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=600',
  '京剧':     'https://img0.baidu.com/it/u=356986736,290025445&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=600',
  // === 陶瓷类（配龙泉/景德镇瓷图）===
  '宜兴紫砂': 'https://img1.baidu.com/it/u=93439799,4086397003&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=600',
  '唐三彩':   'https://img1.baidu.com/it/u=1233339720,1163225280&fm=253&app=138&f=JPEG?w=800&h=600',
  '钧瓷':     'https://img2.baidu.com/it/u=592574936,1567469759&fm=253&app=138&f=JPEG?w=800&h=600',
  '汝瓷':     'https://img0.baidu.com/it/u=3446557113,1651915518&fm=253&app=138&f=JPEG?w=800&h=600',
  // === 织绣类（配苏绣/云锦图）===
  '蜀锦':     'https://img0.baidu.com/it/u=2813365353,4262896668&fm=253&app=138&f=JPEG?w=800&h=1199',
  '南京云锦': 'https://img0.baidu.com/it/u=2191683119,98611471&fm=253&app=138&f=JPEG?w=800&h=1199',
  '缂丝':     'https://img2.baidu.com/it/u=2302228858,1098718046&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=1422',
  '壮锦':     'https://img1.baidu.com/it/u=3319256515,715621132&fm=253&app=138&f=JPEG?w=800&h=600',
  '苗族蜡染': 'https://img0.baidu.com/it/u=73868185,2382671579&fm=253&app=138&f=JPEG?w=800&h=600',
  // === 雕刻/塑类（配木雕/泥塑图）===
  '东阳木雕': 'https://img1.baidu.com/it/u=3149956100,4141672710&fm=253&app=138&f=JPEG?w=800&h=600',
  '玉雕':     'https://img1.baidu.com/it/u=2734779037,2678149192&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=600',
  '泥人张':   'https://img1.baidu.com/it/u=1754143475,3504854567&fm=253&app=138&f=JPEG?w=800&h=600',
  // === 其他工艺类 ===
  '芜湖铁画': 'https://img2.baidu.com/it/u=3944186181,3308544329&fm=253&app=138&f=JPEG?w=800&h=600',
  '木版年画': 'https://img0.baidu.com/it/u=2089789632,2284449305&fm=253&app=138&f=JPEG?w=800&h=600',
  '竹编':     'https://img1.baidu.com/it/u=48848454,2229253322&fm=253&app=138&f=JPEG?w=800&h=600',
  '漆器':     'https://img2.baidu.com/it/u=1307884396,1255048057&fm=253&app=138&f=JPEG?w=800&h=600',
}

// 按 API 返回的技艺顺序取对应图片
function getCraftImage(name: string): string {
  return IMAGES[name] || Object.values(IMAGES)[Math.abs(hashCode(name)) % Object.values(IMAGES).length]
}
function hashCode(s: string): number {
  let h = 0; for (let i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0 } return h
}

const GRADIENTS = [
  'linear-gradient(135deg, #1a3a5c, #2a5a8c, #4a8ab0)',
  'linear-gradient(135deg, #3a2a4a, #5a3a6a, #8a6a9a)',
  'linear-gradient(135deg, #1a3a2a, #2a5a3a, #4a8a5a)',
  'linear-gradient(135deg, #3a1a1a, #5a2a2a, #8a4a3a)',
  'linear-gradient(135deg, #5a2a1a, #7a4a2a, #a06a4a)',
  'linear-gradient(135deg, #2a1a3a, #4a2a5a, #6a4a7a)',
]

const displayCraft = computed(() => allCrafts.value[current.value] || null)
const bgImage = computed(() => displayCraft.value ? getCraftImage(displayCraft.value.name) : '')
const bgGradient = computed(() => GRADIENTS[current.value % GRADIENTS.length])

onMounted(async () => {
  try { allCrafts.value = await getCrafts() } catch {
    allCrafts.value = [{ id: 'jingtailan', name: '景泰蓝' }, { id: 'suxiu', name: '苏绣' }]
  }
  timer = setInterval(next, 4000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })

function next() {
  fading.value = true
  setTimeout(() => { current.value = (current.value + 1) % allCrafts.value.length; fading.value = false }, 500)
}
function prev() {
  fading.value = true
  setTimeout(() => { current.value = (current.value - 1 + allCrafts.value.length) % allCrafts.value.length; fading.value = false }, 500)
}
function goTo(i: number) {
  if (i === current.value) return
  fading.value = true
  setTimeout(() => { current.value = i; fading.value = false }, 500)
}
function explore() {
  if (!displayCraft.value) return
  chat.setPendingQuestion(`介绍一下${displayCraft.value.name}`)
  router.push('/chat')
}
</script>

<template>
  <section class="max-w-6xl mx-auto px-6 mb-20">
    <p class="caption uppercase tracking-wider mb-4" style="font-size: 0.7rem; letter-spacing: 0.08em">
      非遗技艺 · {{ allCrafts.length }} 种
    </p>

    <!-- Carousel -->
    <div
      class="relative w-full h-[320px] sm:h-[400px] rounded-2xl overflow-hidden cursor-pointer group"
      @click="explore"
      style="box-shadow: var(--shadow-md)"
    >
      <!-- Gradient fallback -->
      <div class="absolute inset-0 transition-opacity duration-500" :style="{ background: bgGradient, opacity: fading ? 1 : 0 }" />

      <!-- Image -->
      <img
        :src="bgImage"
        alt=""
        referrerpolicy="no-referrer"
        class="absolute inset-0 w-full h-full object-cover transition-all duration-700"
        :style="{ opacity: fading ? 0 : 1, transform: fading ? 'scale(1.05)' : 'scale(1)' }"
        @error="($event.target as HTMLImageElement).style.display='none'"
      />

      <!-- Overlay -->
      <div class="absolute inset-0" style="background: linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.05) 50%, rgba(0,0,0,0.15) 100%)" />

      <!-- Arrows -->
      <button @click.stop="prev" class="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center text-white/60 hover:text-white hover:bg-white/10 transition-all z-10 border-0 cursor-pointer text-xl">‹</button>
      <button @click.stop="next" class="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center text-white/60 hover:text-white hover:bg-white/10 transition-all z-10 border-0 cursor-pointer text-xl">›</button>

      <!-- Content -->
      <Transition name="slide-up" mode="out-in">
        <div v-if="displayCraft" :key="current" class="absolute bottom-8 left-8 right-16 z-10" style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', 'PingFang SC', serif">
          <div class="text-white/50 text-xs uppercase tracking-widest mb-1" style="font-family: 'Inter', 'PingFang SC', sans-serif">{{ current + 1 }} / {{ allCrafts.length }}</div>
          <div class="text-white text-3xl sm:text-4xl font-bold tracking-tight drop-shadow-lg" style="font-weight: 400">{{ displayCraft.name }}</div>
          <div class="text-white/70 text-sm mt-2 max-w-lg drop-shadow">点击探索 {{ displayCraft.name }} 的技艺世界 →</div>
        </div>
      </Transition>

      <!-- Dots -->
      <div class="absolute bottom-4 right-4 flex gap-1.5 z-10">
        <button
          v-for="i in Math.min(8, allCrafts.length)"
          :key="i"
          @click.stop="goTo(i - 1)"
          class="w-2 h-2 rounded-full border-0 transition-all duration-300 cursor-pointer"
          :style="{ background: i - 1 === current ? '#fff' : 'rgba(255,255,255,0.25)', transform: 'scale(' + (i - 1 === current ? 1.3 : 1) + ')' }"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.4s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(12px); }
.slide-up-leave-to { opacity: 0; transform: translateY(-12px); }
</style>
