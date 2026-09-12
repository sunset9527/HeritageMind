<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { getSessions } from '@/api/chat'
import { getCrafts, getProfiles } from '@/api/meta'
import type { ChatSession, CraftItem, ProfileItem } from '@/types'
import UserBubble from '@/components/chat/UserBubble.vue'
import AgentCard from '@/components/chat/AgentCard.vue'
import GapNotice from '@/components/chat/GapNotice.vue'
import DebateTimeline from '@/components/chat/DebateTimeline.vue'
import CitationList from '@/components/chat/CitationList.vue'
import MarkdownContent from '@/components/chat/MarkdownContent.vue'
import WorkflowTrace from '@/components/chat/WorkflowTrace.vue'
import RealtimeWorkflowDag from '@/components/chat/RealtimeWorkflowDag.vue'
import AnswerFeedback from '@/components/chat/AnswerFeedback.vue'

const chatStore = useChatStore()
const auth = useAuthStore()
const settings = useSettingsStore()
const input = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const sidebarOpen = ref(false)

const profiles = ref<ProfileItem[]>([])
const crafts = ref<CraftItem[]>([])
const sessions = ref<ChatSession[]>([])

onMounted(async () => {
  try { profiles.value = await getProfiles() } catch { /* */ }
  if (!profiles.value.length) {
    profiles.value = [
      { id: 'curious', name: '好奇者', description: '', depth: '300-500字' },
      { id: 'learner', name: '学习者', description: '', depth: '800-1500字' },
      { id: 'researcher', name: '研究者', description: '', depth: '2000+字' },
    ]
  }
  try { crafts.value = await getCrafts() } catch { /* */ }
  if (!crafts.value.length) {
    crafts.value = [
      { id: 'jingtailan', name: '景泰蓝' }, { id: 'suxiu', name: '苏绣' },
      { id: 'longquan_ci', name: '龙泉青瓷' }, { id: 'yixing_zisha', name: '宜兴紫砂' },
      { id: 'wuhu_tiehua', name: '芜湖铁画' }, { id: 'shujin', name: '蜀锦' },
    ]
  }
  if (auth.isAuthenticated) {
    try {
      const response = await getSessions(8)
      sessions.value = response.items
      if (sessions.value.length && !chatStore.activeSessionId) {
        await chatStore.loadSession(sessions.value[0].id)
      }
    } catch { /* */ }
  }
  if (chatStore.pendingQuestion) {
    input.value = chatStore.pendingQuestion
    handleSend()
  }
})

async function handleSend() {
  const q = input.value.trim()
  if (!q || chatStore.isSending) return
  if (!settings.canQuery()) {
    ElMessage.warning('请先在设置中填写你的 API Key')
    return
  }
  input.value = ''
  await chatStore.sendQuestion(q)
  if (auth.isAuthenticated) {
    try { sessions.value = (await getSessions(8)).items } catch { /* */ }
  }
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}

async function continueSession(sessionId: string) {
  try {
    await chatStore.loadSession(sessionId)
    await nextTick()
    scrollToBottom()
  } catch {
    ElMessage.error('加载对话失败')
  }
}

const chipColors: Record<string, { bg: string; color: string; icon: string }> = {
  craft_expert: { bg: 'rgba(91,123,94,0.1)', color: '#5B7B5E', icon: '🎨' },
  history_expert: { bg: 'rgba(74,107,138,0.1)', color: '#4A6B8A', icon: '📜' },
  heritage_expert: { bg: 'rgba(184,120,62,0.1)', color: '#B8783E', icon: '🏛️' },
}
function agentChipBg(id: string) { return chipColors[id]?.bg || 'rgba(0,0,0,0.05)' }
function agentChipColor(id: string) { return chipColors[id]?.color || 'var(--text-secondary)' }
function agentChipIcon(id: string) { return chipColors[id]?.icon || '💬' }
</script>

<template>
  <div class="flex h-[calc(100vh-52px)]">
    <!-- Sidebar — collapsible -->
    <Transition name="slide">
      <aside
        v-if="sidebarOpen"
        class="w-60 flex-shrink-0 border-r overflow-y-auto p-4 flex flex-col gap-3"
        style="background: rgba(249, 247, 244, 0.6); border-color: var(--border)"
      >
        <!-- Auth -->
        <div v-if="auth.isAuthenticated" class="text-sm">
          <div class="font-semibold">{{ auth.user?.username }}</div>
          <button @click="auth.logout()" class="text-xs text-[var(--text-tertiary)] hover:text-[var(--accent)] mt-1">退出</button>
        </div>
        <div v-else class="text-sm space-x-2">
          <router-link to="/login" class="text-[var(--accent)] no-underline font-medium">登录</router-link>
          <router-link to="/register" class="text-[var(--text-tertiary)] no-underline">注册</router-link>
        </div>

        <div class="w-full" style="height: 1px; background: var(--border)" />

        <!-- Profile -->
        <div>
          <div class="text-[11px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1.5">学习深度</div>
          <select
            :value="chatStore.currentProfile"
            @change="chatStore.setProfile(($event.target as HTMLSelectElement).value)"
            class="w-full text-[13px] rounded-lg px-2 py-1.5 bg-white border-0"
            style="box-shadow: var(--shadow-sm)"
          >
            <option v-for="p in profiles" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <!-- Craft -->
        <div>
          <div class="text-[11px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1.5">技艺</div>
          <select
            :value="chatStore.currentCraft || ''"
            @change="chatStore.setCraft(($event.target as HTMLSelectElement).value || null)"
            class="w-full text-[13px] rounded-lg px-2 py-1.5 bg-white border-0"
            style="box-shadow: var(--shadow-sm)"
          >
            <option value="">全部</option>
            <option v-for="c in crafts" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </div>

        <!-- Narrative -->
        <label class="flex items-center gap-2 text-[13px] text-[var(--text-secondary)] cursor-pointer">
          <input type="checkbox" :checked="chatStore.includeNarrative" @change="chatStore.toggleNarrative()" class="rounded" />
          传承人口吻
        </label>

        <div class="w-full" style="height: 1px; background: var(--border)" />

        <!-- Sessions -->
        <div v-if="auth.isAuthenticated">
          <div class="flex items-center justify-between text-[11px] uppercase tracking-wider text-[var(--text-tertiary)] mb-1.5">
            <span>继续上次对话</span>
            <button @click="chatStore.startNewSession()" class="border-0 bg-transparent cursor-pointer text-[var(--accent)] text-[11px]">新对话</button>
          </div>
          <button
            v-for="session in sessions"
            :key="session.id"
            @click="continueSession(session.id)"
            class="w-full text-left text-[12px] truncate py-1 px-1.5 rounded border-0 cursor-pointer"
            :style="{ color: chatStore.activeSessionId === session.id ? 'var(--accent)' : 'var(--text-tertiary)', background: chatStore.activeSessionId === session.id ? 'var(--accent-soft)' : 'transparent' }"
          >
            {{ session.title }}
          </button>
        </div>
      </aside>
    </Transition>

    <!-- Main Chat -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Chat header bar -->
      <div class="flex items-center gap-3 px-6 py-3 border-b" style="border-color: var(--border)">
        <button
          @click="sidebarOpen = !sidebarOpen"
          class="text-[var(--text-tertiary)] hover:text-[var(--text)] transition-colors text-sm"
        >
          {{ sidebarOpen ? '← 收起' : '→ 选项' }}
        </button>
        <span class="text-[13px] text-[var(--text-tertiary)]">
          {{ chatStore.currentProfile === 'curious' ? '好奇者' : chatStore.currentProfile === 'learner' ? '学习者' : '研究者' }}
          <template v-if="chatStore.currentCraft"> · {{ chatStore.currentCraft }}</template>
        </span>
      </div>

      <!-- Quick questions -->
      <div v-if="chatStore.messages.length === 0" class="px-6 pt-6 pb-2">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="q in ['景泰蓝的制作流程是什么？', '苏绣有哪些针法特点？', '龙泉青瓷的釉色如何形成？', '宜兴紫砂壶为什么适合泡茶？', '芜湖铁画的传承现状如何？', '蜀锦与宋锦有什么区别？']"
            :key="q"
            @click="input = q; handleSend()"
            class="px-4 py-2 rounded-full text-[13px] font-medium transition-all duration-300 cursor-pointer border-0"
            style="background: var(--surface); color: var(--text-secondary); box-shadow: var(--shadow-sm); border: 1px solid var(--border)"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto px-6 py-4">
        <template v-for="msg in chatStore.messages" :key="msg.id">
          <UserBubble v-if="msg.role === 'user'" :content="msg.content" :timestamp="msg.timestamp" />
          <template v-else>
            <!-- Agent contributors as small tags -->
            <div v-if="msg.metadata?.sourceAgents?.length" class="flex items-center gap-1.5 mb-2 mt-3">
              <span
                v-for="agent in msg.metadata.sourceAgents"
                :key="agent.id"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium"
                :style="{
                  background: agentChipBg(agent.id),
                  color: agentChipColor(agent.id),
                }"
              >
                {{ agentChipIcon(agent.id) }} {{ agent.type || agent.id }}
              </span>
            </div>
            <!-- Answer content -->
            <div class="mb-3" style="color: var(--text)">
              <MarkdownContent :content="msg.content" />
            </div>
            <GapNotice v-if="msg.metadata?.hasGaps" :text="msg.metadata?.gapReport || ''" />
            <WorkflowTrace
              v-if="msg.metadata?.route && msg.metadata?.workflowTrace?.length"
              :route="msg.metadata.route"
              :trace="msg.metadata.workflowTrace"
              :citations="msg.metadata.citations || []"
            />
            <RealtimeWorkflowDag
              v-if="msg.metadata?.realtimeWorkflow"
              :workflow="msg.metadata.realtimeWorkflow"
            />
            <CitationList v-if="msg.metadata?.citations?.length" :citations="msg.metadata!.citations!" />
            <div v-if="msg.metadata?.evaluation" class="caption mb-2">过程质量信号：{{ msg.metadata.evaluation.total_score }}/100（规则 {{ msg.metadata.evaluation.rule_version }}）</div>
            <AnswerFeedback
              :chat-id="msg.metadata?.chatId"
              :feedback="msg.metadata?.feedback"
              @changed="(feedback) => { if (msg.metadata) msg.metadata.feedback = feedback }"
            />
            <div v-if="msg.metadata?.elapsedMs" class="caption mb-4">
              {{ (msg.metadata.elapsedMs / 1000).toFixed(1) }}s · {{ msg.metadata.model }}
            </div>
          </template>
        </template>
        <div v-if="chatStore.isSending" class="flex items-center gap-2 caption py-4">
          <span class="inline-block w-3.5 h-3.5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          思考中…
        </div>
      </div>

      <!-- Key required notice -->
      <div
        v-if="!settings.canQuery()"
        class="mx-6 mb-2 px-4 py-2.5 rounded-xl text-[13px] flex items-center gap-2"
        style="background: #FFFBF0; color: #8B6D2E; border: 1px solid rgba(180, 140, 60, 0.12)"
      >
        <span>⚠️</span>
        <span>请先填写 API Key 才能提问</span>
        <router-link to="/settings" class="ml-auto font-medium no-underline" style="color: var(--accent)">前往设置 →</router-link>
      </div>

      <!-- Input -->
      <div class="px-6 py-4 border-t" style="border-color: var(--border); background: rgba(249, 247, 244, 0.5)">
        <div class="flex gap-3 max-w-4xl">
          <input
            v-model="input"
            @keyup.enter="handleSend()"
            :disabled="chatStore.isSending || !settings.canQuery()"
            :placeholder="settings.canQuery() ? '提出你的问题…' : '请先在设置页配置 API Key…'"
            class="flex-1 px-5 py-3 rounded-2xl text-[14px] transition-all duration-300 border-0"
            style="background: var(--surface); box-shadow: var(--shadow-sm); outline: none"
            @focus="($event.target as HTMLElement).style.boxShadow = '0 0 0 3px var(--accent-soft)'"
            @blur="($event.target as HTMLElement).style.boxShadow = 'var(--shadow-sm)'"
          />
          <button
            @click="handleSend()"
            :disabled="chatStore.isSending || !input.trim() || !settings.canQuery()"
            class="px-6 py-3 rounded-2xl text-[14px] font-semibold transition-all duration-300 border-0 cursor-pointer disabled:opacity-30"
            style="background: var(--text); color: #fff"
          >
            发送
          </button>
        </div>
      </div>
    </div>

    <!-- Debate panel (right) -->
    <aside class="w-72 flex-shrink-0 border-l p-4 overflow-y-auto hidden xl:block" style="border-color: var(--border); background: rgba(249, 247, 244, 0.3)">
      <div class="text-[11px] uppercase tracking-wider text-[var(--text-tertiary)] mb-3">辩论过程</div>
      <template v-if="chatStore.messages.length">
        <DebateTimeline
          :debate-session="chatStore.messages[chatStore.messages.length - 1]?.metadata?.debateSession || null"
          :source-agents="chatStore.messages[chatStore.messages.length - 1]?.metadata?.sourceAgents || []"
        />
      </template>
      <div v-else class="caption text-center pt-8">提问后展示</div>
    </aside>
  </div>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all 0.3s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateX(-16px); }
</style>
