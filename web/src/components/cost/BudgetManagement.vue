<template>
  <div class="card--od--refined p-6">
    <h2 class="text-xl font-semibold text-white mb-6">{{ $t('cost.budget.title') }}</h2>
    
    <!-- 预算设置表单 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
      <!-- 日预算设置 -->
      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--od-text-secondary)">
          {{ $t('cost.budget.dailyLimit') }}
        </label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2" style="color: var(--od-text-muted)">$</span>
          <input
            v-model.number="dailyBudget"
            type="number"
            min="0"
            step="0.01"
            class="input--od pl-8 w-full"
            @change="updateBudget"
          />
        </div>
        <p class="text-xs mt-1" style="color: var(--od-text-muted)">
          {{ $t('cost.budget.currentUsage') }}: ${{ costStore.currentCost.dailyCost.toFixed(2) }}
          ({{ costStore.dailyBudgetUsage.toFixed(1) }}%)
        </p>
      </div>
      
      <!-- 月预算设置 -->
      <div>
        <label class="block text-sm font-medium mb-2" style="color: var(--od-text-secondary)">
          {{ $t('cost.budget.monthlyLimit') }}
        </label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2" style="color: var(--od-text-muted)">$</span>
          <input
            v-model.number="monthlyBudget"
            type="number"
            min="0"
            step="0.01"
            class="input--od pl-8 w-full"
            @change="updateBudget"
          />
        </div>
        <p class="text-xs mt-1" style="color: var(--od-text-muted)">
          {{ $t('cost.budget.currentUsage') }}: ${{ costStore.currentCost.monthlyCost.toFixed(2) }}
          ({{ costStore.monthlyBudgetUsage.toFixed(1) }}%)
        </p>
      </div>
    </div>
    
    <!-- 预算使用进度 -->
    <div class="space-y-4 mb-8">
      <!-- 日预算进度 -->
      <div>
        <div class="flex justify-between text-sm mb-2">
          <span style="color: var(--od-text-secondary)">{{ $t('cost.budget.dailyProgress') }}</span>
          <span :style="{ color: costStore.dailyBudgetUsage > 100 ? 'var(--od-color-error)' : 'var(--od-text-muted)' }">
            ${{ costStore.currentCost.dailyCost.toFixed(2) }} / ${{ costStore.currentCost.budget.daily }}
          </span>
        </div>
        <div class="w-full rounded-full h-2" style="background: var(--od-bg-secondary)">
          <div 
            class="h-2 rounded-full transition-all duration-300"
            :class="getBudgetProgressClass(costStore.dailyBudgetUsage)"
            :style="{ width: `${Math.min(costStore.dailyBudgetUsage, 100)}%` }"
          ></div>
        </div>
      </div>
      
      <!-- 月预算进度 -->
      <div>
        <div class="flex justify-between text-sm mb-2">
          <span style="color: var(--od-text-secondary)">{{ $t('cost.budget.monthlyProgress') }}</span>
          <span :style="{ color: costStore.monthlyBudgetUsage > 100 ? 'var(--od-color-error)' : 'var(--od-text-muted)' }">
            ${{ costStore.currentCost.monthlyCost.toFixed(2) }} / ${{ costStore.currentCost.budget.monthly }}
          </span>
        </div>
        <div class="w-full rounded-full h-2" style="background: var(--od-bg-secondary)">
          <div 
            class="h-2 rounded-full transition-all duration-300"
            :class="getBudgetProgressClass(costStore.monthlyBudgetUsage)"
            :style="{ width: `${Math.min(costStore.monthlyBudgetUsage, 100)}%` }"
          ></div>
        </div>
      </div>
    </div>
    
    <!-- 预算警报设置 -->
    <div class="border-t border-slate-700 pt-6">
      <h3 class="text-lg font-medium text-white mb-4">{{ $t('cost.budget.alertSettings') }}</h3>
      
      <div class="space-y-4">
        <!-- 警报阈值 -->
        <div>
          <label class="block text-sm font-medium mb-2" style="color: var(--od-text-secondary)">
            {{ $t('cost.budget.alertThreshold') }}
          </label>
          <div class="flex items-center space-x-4">
            <input
              v-model.number="alertThreshold"
              type="range"
              min="50"
              max="95"
              step="5"
              class="flex-1 range-slider"
              @change="updateAlertSettings"
            />
            <span class="font-medium w-12 text-right" style="color: var(--od-text-primary)">{{ alertThreshold }}%</span>
          </div>
          <p class="text-xs mt-1" style="color: var(--od-text-muted)">
            {{ $t('cost.budget.alertThresholdHint') }}
          </p>
        </div>
        
        <!-- 启用警报 -->
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.budget.enableAlerts') }}</p>
            <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.budget.enableAlertsHint') }}</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input 
              v-model="alertsEnabled"
              type="checkbox" 
              class="sr-only peer"
              @change="updateAlertSettings"
            >
            <div class="w-11 h-6 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all" :style="{ background: alertsEnabled ? 'var(--od-color-primary)' : 'var(--od-bg-secondary)' }"></div>
          </label>
        </div>
      </div>
    </div>
    
    <!-- 保存按钮 -->
    <div class="mt-6 flex justify-end">
      <button
        @click="saveSettings"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
        :disabled="saving"
      >
        <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        {{ saving ? $t('common.saving') : $t('common.save') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'
import { useSimpleToast } from '@/composables/useSimpleToast'

const { t } = useI18n()
const costStore = useCostStore()
const { showSuccess, showError } = useSimpleToast()

// 响应式数据
const dailyBudget = ref(50)
const monthlyBudget = ref(1000)
const alertThreshold = ref(80)
const alertsEnabled = ref(true)
const saving = ref(false)

// 获取进度条颜色类
const getBudgetProgressClass = (usage: number): string => {
  if (usage >= 100) return 'bg-red-500'
  if (usage >= 80) return 'bg-yellow-500'
  return 'bg-green-500'
}

// 更新预算
const updateBudget = async () => {
  try {
    await costStore.setBudget(dailyBudget.value, monthlyBudget.value)
  } catch (error) {
    showError(t('cost.budget.updateError'))
  }
}

// 更新警报设置
const updateAlertSettings = () => {
  costStore.updateAlertSettings({
    dailyThreshold: alertThreshold.value / 100,
    monthlyThreshold: alertThreshold.value / 100,
    enableAlerts: alertsEnabled.value
  })
}

// 保存所有设置
const saveSettings = async () => {
  saving.value = true
  try {
    await updateBudget()
    updateAlertSettings()
    showSuccess(t('cost.budget.saveSuccess'))
  } catch (error) {
    showError(t('cost.budget.saveError'))
  } finally {
    saving.value = false
  }
}

// 初始化数据
onMounted(() => {
  dailyBudget.value = costStore.currentCost.budget.daily
  monthlyBudget.value = costStore.currentCost.budget.monthly
  alertThreshold.value = costStore.alertSettings.dailyThreshold * 100
  alertsEnabled.value = costStore.alertSettings.enableAlerts
})
</script>

<style scoped>
/* 自定义滑块样式 */
.range-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 8px;
  background: var(--od-bg-secondary);
  border-radius: 4px;
  outline: none;
  transition: all 0.3s ease;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: var(--od-color-primary);
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.range-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: var(--od-color-primary);
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.range-slider:hover::-webkit-slider-thumb {
  transform: scale(1.1);
}

.range-slider:hover::-moz-range-thumb {
  transform: scale(1.1);
}

/* 进度条颜色保持原有的Tailwind类 */
</style>