<template>
  <div class="card--od--refined p-6">
    <h2 class="text-xl font-semibold mb-6" style="color: var(--od-text-primary)">{{ $t('cost.alerts.title') }}</h2>
    
    <!-- 当前预警状态 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
      <!-- 日预算预警 -->
      <div 
        class="rounded-lg p-4 border-2"
        :class="getDailyAlertClass()"
      >
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-medium mb-1" style="color: var(--od-text-primary)">{{ $t('cost.alerts.dailyBudget') }}</h3>
            <p class="text-sm" style="color: var(--od-text-secondary)">
              {{ $t('cost.alerts.usage') }}: ${{ costStore.currentCost.dailyCost.toFixed(2) }} 
              / ${{ costStore.currentCost.budget.daily }}
            </p>
            <p class="text-xs mt-1">
              {{ getDailyAlertMessage() }}
            </p>
          </div>
          <div class="text-2xl">
            {{ getDailyAlertIcon() }}
          </div>
        </div>
      </div>
      
      <!-- 月预算预警 -->
      <div 
        class="rounded-lg p-4 border-2"
        :class="getMonthlyAlertClass()"
      >
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-medium mb-1" style="color: var(--od-text-primary)">{{ $t('cost.alerts.monthlyBudget') }}</h3>
            <p class="text-sm" style="color: var(--od-text-secondary)">
              {{ $t('cost.alerts.usage') }}: ${{ costStore.currentCost.monthlyCost.toFixed(2) }} 
              / ${{ costStore.currentCost.budget.monthly }}
            </p>
            <p class="text-xs mt-1">
              {{ getMonthlyAlertMessage() }}
            </p>
          </div>
          <div class="text-2xl">
            {{ getMonthlyAlertIcon() }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- 预警历史 -->
    <div class="mb-6">
      <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.alerts.history') }}</h3>
      <div class="space-y-2 max-h-64 overflow-y-auto">
        <div
          v-for="alert in alertHistory"
          :key="alert.id"
          class="flex items-start space-x-3 p-3 rounded-lg" style="background: var(--od-bg-secondary)"
        >
          <div class="text-lg">{{ getAlertTypeIcon(alert.type) }}</div>
          <div class="flex-1">
            <p class="text-sm" style="color: var(--od-text-primary)">{{ alert.message }}</p>
            <p class="text-xs" style="color: var(--od-text-muted)">{{ formatDate(alert.timestamp) }}</p>
          </div>
          <button
            @click="dismissAlert(alert.id)"
            class="hover:opacity-80" style="color: var(--od-text-muted)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      
      <div v-if="alertHistory.length === 0" class="text-center py-8" style="color: var(--od-text-muted)">
        {{ $t('cost.alerts.noHistory') }}
      </div>
    </div>
    
    <!-- 预警规则配置 -->
    <div class="border-t pt-6" style="border-color: var(--od-border)">
      <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.alerts.rules') }}</h3>
      <div class="space-y-4">
        <!-- 超预算预警 -->
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.alerts.budgetExceeded') }}</p>
            <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.alerts.budgetExceededHint') }}</p>
          </div>
          <input 
            v-model="rules.budgetExceeded"
            type="checkbox" 
            class="form-check-input"
          >
        </div>
        
        <!-- 接近预算预警 -->
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.alerts.nearBudget') }}</p>
            <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.alerts.nearBudgetHint') }}</p>
          </div>
          <input 
            v-model="rules.nearBudget"
            type="checkbox" 
            class="form-check-input"
          >
        </div>
        
        <!-- 异常高成本预警 -->
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.alerts.unusualSpike') }}</p>
            <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.alerts.unusualSpikeHint') }}</p>
          </div>
          <input 
            v-model="rules.unusualSpike"
            type="checkbox" 
            class="form-check-input"
          >
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'

const { t } = useI18n()
const costStore = useCostStore()

// 响应式数据
interface Alert {
  id: string
  type: 'warning' | 'danger' | 'info'
  message: string
  timestamp: number
}

const alertHistory = ref<Alert[]>([])
const rules = ref({
  budgetExceeded: true,
  nearBudget: true,
  unusualSpike: true
})

// 获取日预算预警样式
const getDailyAlertClass = () => {
  const usage = costStore.dailyBudgetUsage
  if (usage >= 100) return 'border-red-500'
  if (usage >= 80) return 'border-yellow-500'
  return 'border-green-500'
}

// 获取月预算预警样式
const getMonthlyAlertClass = () => {
  const usage = costStore.monthlyBudgetUsage
  if (usage >= 100) return 'border-red-500'
  if (usage >= 80) return 'border-yellow-500'
  return 'border-green-500'
}

// 获取日预算预警消息
const getDailyAlertMessage = () => {
  const usage = costStore.dailyBudgetUsage
  if (usage >= 100) return t('cost.alerts.dailyExceeded')
  if (usage >= 80) return t('cost.alerts.dailyWarning')
  return t('cost.alerts.dailyNormal')
}

// 获取月预算预警消息
const getMonthlyAlertMessage = () => {
  const usage = costStore.monthlyBudgetUsage
  if (usage >= 100) return t('cost.alerts.monthlyExceeded')
  if (usage >= 80) return t('cost.alerts.monthlyWarning')
  return t('cost.alerts.monthlyNormal')
}

// 获取预警图标
const getDailyAlertIcon = () => {
  const usage = costStore.dailyBudgetUsage
  if (usage >= 100) return '🚨'
  if (usage >= 80) return '⚠️'
  return '✅'
}

const getMonthlyAlertIcon = () => {
  const usage = costStore.monthlyBudgetUsage
  if (usage >= 100) return '🚨'
  if (usage >= 80) return '⚠️'
  return '✅'
}

const getAlertTypeIcon = (type: string) => {
  const icons = {
    warning: '⚠️',
    danger: '🚨',
    info: 'ℹ️'
  }
  return icons[type as keyof typeof icons] || 'ℹ️'
}

// 格式化日期
const formatDate = (timestamp: number) => {
  return new Date(timestamp).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 关闭预警
const dismissAlert = (id: string) => {
  const index = alertHistory.value.findIndex(a => a.id === id)
  if (index > -1) {
    alertHistory.value.splice(index, 1)
  }
}

// 检查并生成预警
const checkAlerts = () => {
  const now = Date.now()
  
  // 检查日预算
  if (rules.value.budgetExceeded && costStore.isDailyBudgetExceeded) {
    alertHistory.value.unshift({
      id: `daily-exceeded-${now}`,
      type: 'danger',
      message: t('cost.alerts.dailyBudgetExceededMessage', { 
        amount: costStore.currentCost.dailyCost.toFixed(2),
        budget: costStore.currentCost.budget.daily
      }),
      timestamp: now
    })
  } else if (rules.value.nearBudget && costStore.shouldShowDailyAlert) {
    alertHistory.value.unshift({
      id: `daily-warning-${now}`,
      type: 'warning',
      message: t('cost.alerts.dailyBudgetWarningMessage', {
        percentage: costStore.dailyBudgetUsage.toFixed(1)
      }),
      timestamp: now
    })
  }
  
  // 检查月预算
  if (rules.value.budgetExceeded && costStore.isMonthlyBudgetExceeded) {
    alertHistory.value.unshift({
      id: `monthly-exceeded-${now}`,
      type: 'danger',
      message: t('cost.alerts.monthlyBudgetExceededMessage', {
        amount: costStore.currentCost.monthlyCost.toFixed(2),
        budget: costStore.currentCost.budget.monthly
      }),
      timestamp: now
    })
  } else if (rules.value.nearBudget && costStore.shouldShowMonthlyAlert) {
    alertHistory.value.unshift({
      id: `monthly-warning-${now}`,
      type: 'warning',
      message: t('cost.alerts.monthlyBudgetWarningMessage', {
        percentage: costStore.monthlyBudgetUsage.toFixed(1)
      }),
      timestamp: now
    })
  }
  
  // 限制历史记录数量
  if (alertHistory.value.length > 50) {
    alertHistory.value = alertHistory.value.slice(0, 50)
  }
}

// 监听成本变化
watch(() => costStore.currentCost, () => {
  if (costStore.alertSettings.enableAlerts) {
    checkAlerts()
  }
}, { deep: true })

// 初始化
onMounted(() => {
  checkAlerts()
})
</script>