import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'HeritageMind' },
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: 'AI 问答' },
  },
  {
    path: '/graph',
    name: 'graph',
    component: () => import('@/views/GraphView.vue'),
    meta: { title: '知识图谱' },
  },
  {
    path: '/media',
    name: 'media',
    component: () => import('@/views/MediaView.vue'),
    meta: { title: '多媒体' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置' },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { title: '管理后台', requiresAdmin: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: '注册', guest: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '404' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title} - HeritageMind`
  if (to.meta.requiresAdmin) {
    const saved = localStorage.getItem('heritagemind_user')
    const user = saved ? JSON.parse(saved) : null
    if (user?.role !== 'admin') return next('/chat')
  }
  next()
})

export default router
