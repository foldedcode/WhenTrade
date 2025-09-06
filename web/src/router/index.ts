import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    // 主布局路由（带导航栏）
    {
      path: '/',
      component: () => import('../layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: Home
        },
        {
          path: 'cost-control',
          name: 'cost-control',
          component: () => import('../views/CostControl.vue'),
          meta: {
            titleKey: 'cost.pageTitle'
          }
        },
        {
          path: 'collaboration',
          name: 'collaboration',
          component: () => import('../views/CollaborationSimple.vue'),
          meta: {
            titleKey: 'collaboration.pageTitle'
          }
        },
        {
          path: 'dynamic-analysis',
          name: 'dynamic-analysis',
          component: () => import('../views/DynamicAnalysis.vue'),
          meta: {
            titleKey: 'dynamicAnalysis.pageTitle'
          }
        },
      ]
    }
  ]
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 动态导入 i18n
  const { default: i18n } = await import('../locales')
  
  // 设置页面标题
  if (to.meta?.title) {
    document.title = to.meta.title as string
  } else if (to.meta?.titleKey) {
    // 使用 i18n 翻译标题
    const translatedTitle = i18n.global.t(to.meta.titleKey as string)
    document.title = `${translatedTitle} - When.Trade`
  } else {
    document.title = 'When.Trade'
  }
  
  next()
})

export default router