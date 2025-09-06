<template>
  <div class="min-h-screen bg-slate-900 p-6">
    <div class="max-w-7xl mx-auto">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-white mb-2">{{ $t('cost.title') }}</h1>
        <p class="text-slate-400">{{ $t('cost.subtitle') }}</p>
      </div>

      <!-- 实时成本监控卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <!-- 模型计费（按提供商，仅显示已配置的API） -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700 md:col-span-2">
          <div class="flex items-center justify-between mb-3">
            <span class="text-slate-400 text-sm">模型计费</span>
            <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div v-if="costStore.providerUsage.length > 0" class="space-y-2">
            <div v-for="u in costStore.providerUsage" :key="u.id" class="flex items-center justify-between py-1">
              <span class="text-slate-300">{{ u.label }}已使用</span>
              <span class="text-white font-semibold">{{ u.amountText }}</span>
            </div>
          </div>
          <div v-else class="text-slate-500 text-sm">未检测到可用的 API，请在后端配置相应的密钥。</div>
        </div>
        <!-- 今日成本 -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div class="flex items-center justify-between mb-2">
            <span class="text-slate-400 text-sm">{{ $t('cost.todayCost') }}</span>
            <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="text-2xl font-bold text-white mb-1">
            ${{ costStore.currentCost.dailyCost.toFixed(2) }}
          </div>
          <div class="flex items-center justify-between">
            <span class="text-xs text-slate-500">{{ $t('cost.budget') }}: ${{ costStore.currentCost.budget.daily }}</span>
            <span class="text-xs" :class="costStore.dailyBudgetUsage > 80 ? 'text-red-400' : 'text-green-400'">
              {{ costStore.dailyBudgetUsage.toFixed(1) }}%
            </span>
          </div>
        </div>

        <!-- 本月成本 -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div class="flex items-center justify-between mb-2">
            <span class="text-slate-400 text-sm">{{ $t('cost.monthlyCost') }}</span>
            <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div class="text-2xl font-bold text-white mb-1">
            ${{ costStore.currentCost.monthlyCost.toFixed(2) }}
          </div>
          <div class="flex items-center justify-between">
            <span class="text-xs text-slate-500">{{ $t('cost.budget') }}: ${{ costStore.currentCost.budget.monthly }}</span>
            <span class="text-xs" :class="costStore.monthlyBudgetUsage > 80 ? 'text-red-400' : 'text-green-400'">
              {{ costStore.monthlyBudgetUsage.toFixed(1) }}%
            </span>
          </div>
        </div>

        <!-- Token使用量 -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div class="flex items-center justify-between mb-2">
            <span class="text-slate-400 text-sm">{{ $t('cost.totalTokens') }}</span>
            <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div class="text-2xl font-bold text-white mb-1">
            {{ formatNumber(costStore.totalTokens) }}
          </div>
          <div class="text-xs text-slate-500">
            {{ $t('cost.averageCostPerToken') }}: ${{ (costStore.totalCost / (costStore.totalTokens || 1) * 1000).toFixed(4) }}
          </div>
        </div>

        <!-- 优化建议 -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div class="flex items-center justify-between mb-2">
            <span class="text-slate-400 text-sm">{{ $t('cost.potentialSavings') }}</span>
            <svg class="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div class="text-2xl font-bold text-white mb-1">
            ${{ costStore.totalPotentialSavings.toFixed(2) }}
          </div>
          <div class="text-xs text-slate-500">
            {{ costStore.unimplementedSuggestions }} {{ $t('cost.optimizationsPending') }}
          </div>
        </div>
      </div>

      <!-- 功能选项卡 -->
      <div class="bg-slate-800 rounded-lg p-1 mb-8">
        <nav class="flex space-x-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="flex-1 px-4 py-3 text-sm font-medium rounded-lg transition-colors"
            :class="activeTab === tab.id
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-slate-300 hover:text-white hover:bg-slate-700'"
          >
            <span class="mr-2">{{ tab.icon }}</span>
            {{ tab.name }}
          </button>
        </nav>
      </div>

      <!-- 内容区域 -->
      <div class="space-y-8">
        <!-- Token使用分析 -->
        <div v-if="activeTab === 'usage'" class="space-y-6">
          <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <!-- 主要图表区域 -->
            <div class="xl:col-span-2 space-y-6">
              <TokenUsageChart />
              <CostBreakdown />
            </div>
            <!-- 右侧最近分析区域 -->
            <div class="xl:col-span-1">
              <RecentAnalyses />
            </div>
          </div>
        </div>

        <!-- 预算管理 -->
        <div v-if="activeTab === 'budget'" class="space-y-6">
          <BudgetManagement />
          <CostAlerts />
        </div>

        <!-- 优化建议 -->
        <div v-if="activeTab === 'optimization'" class="space-y-6">
          <CostOptimizationPanel />
          <ModelRecommendations />
        </div>

        <!-- 成本报表 -->
        <div v-if="activeTab === 'reports'" class="space-y-6">
          <CostReports />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'

// 导入组件
import TokenUsageChart from '@/components/cost/TokenUsageChart.vue'
import CostOptimizationPanel from '@/components/cost/CostOptimizationPanel.vue'
import BudgetManagement from '@/components/cost/BudgetManagement.vue'
import CostBreakdown from '@/components/cost/CostBreakdown.vue'
import CostAlerts from '@/components/cost/CostAlerts.vue'
import ModelRecommendations from '@/components/cost/ModelRecommendations.vue'
import CostReports from '@/components/cost/CostReports.vue'
import RecentAnalyses from '@/components/cost/RecentAnalyses.vue'

const { t } = useI18n()
const costStore = useCostStore()

// 当前激活的选项卡
const activeTab = ref('usage')

// 选项卡配置
const tabs = computed(() => [
  {
    id: 'usage',
    name: t('cost.tabs.usage'),
    icon: '📊'
  },
  {
    id: 'budget',
    name: t('cost.tabs.budget'),
    icon: '💰'
  },
  {
    id: 'optimization',
    name: t('cost.tabs.optimization'),
    icon: '💡'
  },
  {
    id: 'reports',
    name: t('cost.tabs.reports'),
    icon: '📈'
  }
])

// 格式化数字
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

// 初始化成本数据
onMounted(async () => {
  await costStore.initializeApiData()
  
  // 设置定时刷新（每分钟更新一次）
  setInterval(() => {
    costStore.fetchUsageSummary()
  }, 60000)
})
</script>

<style scoped>
/* 保持简洁的样式 */
</style>
