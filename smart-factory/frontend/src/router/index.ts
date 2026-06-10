import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
    },
    {
      path: '/history',
      name: 'HistoryData',
      component: () => import('@/views/HistoryData.vue'),
    },
    {
      path: '/alarms',
      name: 'AlarmConfig',
      component: () => import('@/views/AlarmConfig.vue'),
    },
  ],
})

export default router
