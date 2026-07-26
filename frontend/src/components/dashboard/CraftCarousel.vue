<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { getCrafts } from '@/api/meta'
import type { CraftItem } from '@/types'

const router = useRouter()
const chat = useChatStore()

// 技艺文化描述
const CRAFT_TAGS: Record<string, string> = {
  '景泰蓝': '铜胎掐丝珐琅 · 北京宫廷技艺 · 六百年璀璨传承',
  '苏绣': '四大名绣之首 · 以针作画 · 精细雅洁的东方美学',
  '龙泉青瓷': '青瓷巅峰 · 哥窑冰裂纹 · 粉青梅子青釉色传奇',
  '宜兴紫砂': '陶都瑰宝 · 一壶一世界 · 茶道精神的最佳载体',
  '芜湖铁画': '以锤代笔 · 以铁为墨 · 独一无二的金属工艺画',
  '蜀锦': '丝绸之路锦绣华章 · 两千年的织造智慧',
  '剪纸': '一把剪刀一张纸 · 两千年的指尖乾坤 · 人类非遗',
  '景德镇瓷器': '白如玉明如镜薄如纸声如磬 · 千年瓷都不熄的窑火',
  '南京云锦': '寸锦寸金 · 织中之圣 · 皇家织造的巅峰技艺',
  '东阳木雕': '千年木雕之乡 · 平面浮雕见长 · 散点透视构图',
  '苗族蜡染': '铜刀作笔蜂蜡为墨 · 冰纹天成 · 蝴蝶妈妈的传说',
  '木版年画': '中国年文化的视觉符号 · 一刀一版间的祈福迎祥',
  '缂丝': '通经断纬 · 织中之圣 · 一寸缂丝一寸金',
  '竹编': '劈竹成丝 · 指尖经纬 · 七千年的编织智慧',
  '玉雕': '切磋琢磨 · 君子比德于玉 · 八千年的玉文化',
  '漆器': '百里千刀一斤漆 · 漆黑如夜光润如玉 · 八千年传承',
  '唐三彩': '入窑一色出窑万彩 · 盛唐气象的陶瓷绝唱',
  '钧瓷': '入窑一色出窑万彩 · 窑变无双 · 家有万贯不如钧瓷一片',
  '汝瓷': '雨过天青云破处 · 宋徽宗的极致审美 · 存世不足百件',
  '泥人张': '袖中捏塑须臾成像 · 百年传承的指尖生命',
  '皮影戏': '一口道尽千古事 · 双手对舞百万兵 · 最早的动画',
  '壮锦': '棉纱为经彩丝为纬 · 壮族千年织造智慧',
  '京剧': '唱念做打 · 生旦净丑 · 东方歌剧的极致之美',
}

const allCrafts = ref<CraftItem[]>([])
const current = ref(0)
const fading = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const displayCraft = computed(() => allCrafts.value[current.value] || null)
const craftTag = computed(() => displayCraft.value ? (CRAFT_TAGS[displayCraft.value.name] || '') : '')
const bgImage = computed(() => displayCraft.value ? `/crafts/${displayCraft.value.name}.jpg` : '')

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

    <!-- Carousel: 全宽图片 + 文字在模糊层上 -->
    <div
      class="relative w-full h-[360px] sm:h-[420px] rounded-2xl overflow-hidden cursor-pointer group"
      @click="explore"
      style="box-shadow: var(--shadow-md)"
    >
      <!-- Blurred background fill -->
      <img v-if="displayCraft" :key="'bg-' + current" :src="bgImage" alt=""
        class="absolute inset-0 w-full h-full object-cover blur-xl scale-110"
        :style="{ opacity: fading ? 0.3 : 0.5 }"
      />
      <!-- Main image -->
      <img v-if="displayCraft" :key="'img-' + current" :src="bgImage" :alt="displayCraft.name"
        class="absolute inset-0 w-full h-full object-contain transition-all duration-700"
        :style="{ opacity: fading ? 0 : 1, transform: fading ? 'scale(1.05)' : 'scale(1)' }"
      />

      <!-- Text on blur layer -->
      <Transition name="slide-up" mode="out-in">
        <div v-if="displayCraft" :key="current"
          class="absolute inset-0 z-10 flex items-center justify-between px-6 md:px-10 pointer-events-none"
        >
          <!-- 左侧：名称（横排） -->
          <div class="flex flex-col items-start">
            <div class="text-white/40 text-xs tracking-widest mb-1" style="font-family: 'Inter', 'PingFang SC', sans-serif">
              {{ current + 1 }} / {{ allCrafts.length }}
            </div>
            <div class="text-white text-3xl md:text-4xl font-bold tracking-wide drop-shadow-lg"
              style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', serif; font-weight: 400; writing-mode: horizontal-tb;">
              {{ displayCraft.name }}
            </div>
          </div>

          <!-- 右侧：描述（竖排 · 强阴影浮字） -->
          <div v-if="craftTag"
            class="text-white text-lg md:text-xl tracking-widest leading-loose"
            style="font-family: 'Ma Shan Zheng', 'Zhi Mang Xing', 'STKaiti', 'KaiTi', serif; writing-mode: vertical-rl; max-height: 320px; letter-spacing: 0.2em; text-shadow: 0 1px 6px rgba(0,0,0,0.7), 0 0 12px rgba(0,0,0,0.5), 0 0 24px rgba(0,0,0,0.3);"
          >
            {{ craftTag.replace(/ · /g, '\n') }}
          </div>
        </div>
      </Transition>

      <!-- Arrows -->
      <button @click.stop="prev" class="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full flex items-center justify-center text-white/50 hover:text-white hover:bg-white/10 transition-all z-20 border-0 cursor-pointer text-lg pointer-events-auto">‹</button>
      <button @click.stop="next" class="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full flex items-center justify-center text-white/50 hover:text-white hover:bg-white/10 transition-all z-20 border-0 cursor-pointer text-lg pointer-events-auto">›</button>

      <!-- Dots -->
      <div class="absolute bottom-4 right-4 flex gap-1 z-20 pointer-events-auto">
        <button v-for="i in Math.min(8, allCrafts.length)" :key="i" @click.stop="goTo(i - 1)"
          class="w-1.5 h-1.5 rounded-full border-0 transition-all duration-300 cursor-pointer"
          :style="{ background: i - 1 === current ? '#fff' : 'rgba(255,255,255,0.3)', transform: 'scale(' + (i - 1 === current ? 1.3 : 1) + ')' }"
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
