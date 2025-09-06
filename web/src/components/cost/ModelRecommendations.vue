<template>
  <div class="card--od--refined p-6">
    <h2 class="text-lg font-semibold mb-6" style="color: var(--od-text-primary)">{{ $t('cost.recommendations.title') }}</h2>
    
    <!-- 模型对比表 -->
    <div class="overflow-x-auto mb-8">
      <table class="w-full">
        <thead>
          <tr class="border-b" style="border-color: var(--od-border)">
            <th class="text-left py-3 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.recommendations.model') }}</th>
            <th class="text-center py-3 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.recommendations.inputPrice') }}</th>
            <th class="text-center py-3 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.recommendations.outputPrice') }}</th>
            <th class="text-center py-3 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.recommendations.quality') }}</th>
            <th class="text-center py-3 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.recommendations.speed') }}</th>
            <th class="text-center py-3 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.recommendations.recommended') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="model in models"
            :key="model.name"
            class="border-b hover:bg--od--secondary transition-colors"
            style="border-color: var(--od-border)"
          >
            <td class="py-3 px-4">
              <div class="flex items-center space-x-2">
                <span class="font-medium" style="color: var(--od-text-primary)">{{ model.name }}</span>
                <span v-if="model.isCurrent" class="text-xs px-2 py-0.5 rounded" style="background: rgba(var(--od-color-primary-rgb), 0.2); color: var(--od-color-primary)">
                  {{ $t('cost.recommendations.current') }}
                </span>
              </div>
            </td>
            <td class="text-center py-3 px-4" style="color: var(--od-text-secondary)">${{ model.inputPrice }}/1K</td>
            <td class="text-center py-3 px-4" style="color: var(--od-text-secondary)">${{ model.outputPrice }}/1K</td>
            <td class="text-center py-3 px-4">
              <div class="flex justify-center">
                <div class="flex space-x-1">
                  <span v-for="i in 5" :key="i" :style="{ color: i <= model.quality ? 'var(--od-color-warning)' : 'var(--od-text-muted)' }">★</span>
                </div>
              </div>
            </td>
            <td class="text-center py-3 px-4">
              <div class="flex justify-center">
                <div class="flex space-x-1">
                  <span v-for="i in 5" :key="i" :style="{ color: i <= model.speed ? 'var(--od-color-success)' : 'var(--od-text-muted)' }">●</span>
                </div>
              </div>
            </td>
            <td class="text-center py-3 px-4">
              <span 
                v-if="model.recommended"
                class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
                style="background: rgba(var(--od-color-success-rgb), 0.2); color: var(--od-color-success)"
              >
                {{ model.recommendedFor }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- 智能推荐 -->
    <div class="space-y-4">
      <h3 class="text-base font-medium" style="color: var(--od-text-primary)">{{ $t('cost.recommendations.smartSuggestions') }}</h3>
      
      <!-- 基于使用模式的推荐 -->
      <div class="card--od--refined p-4">
        <div class="flex items-start space-x-3">
          <div class="text-2xl">💡</div>
          <div class="flex-1">
            <h4 class="font-medium mb-1" style="color: var(--od-text-primary)">{{ recommendation.title }}</h4>
            <p class="text-sm mb-3" style="color: var(--od-text-secondary)">{{ recommendation.description }}</p>
            <div class="flex items-center justify-between">
              <div class="text-sm">
                <span style="color: var(--od-text-muted)">{{ $t('cost.recommendations.estimatedSavings') }}:</span>
                <span class="font-medium ml-1" style="color: var(--od-color-success)">${{ recommendation.savings }}/{{ $t('cost.recommendations.month') }}</span>
              </div>
              <button
                @click="applyRecommendation"
                class="btn--od btn--od--primary btn--od--sm"
              >
                {{ $t('cost.recommendations.apply') }}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 模型选择策略 -->
      <div class="card--od--refined p-4">
        <h4 class="font-medium mb-3" style="color: var(--od-text-primary)">{{ $t('cost.recommendations.selectionStrategy') }}</h4>
        <div class="space-y-2">
          <label class="flex items-center space-x-3 cursor-pointer">
            <input
              v-model="strategy"
              type="radio"
              value="balanced"
              @change="updateStrategy('balanced')"
              class="form-check-input"
            >
            <div>
              <p class="text-sm" style="color: var(--od-text-primary)">{{ $t('cost.recommendations.strategies.balanced') }}</p>
              <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.recommendations.strategies.balancedHint') }}</p>
            </div>
          </label>
          <label class="flex items-center space-x-3 cursor-pointer">
            <input
              v-model="strategy"
              type="radio"
              value="cost"
              @change="updateStrategy('cost')"
              class="form-check-input"
            >
            <div>
              <p class="text-sm" style="color: var(--od-text-primary)">{{ $t('cost.recommendations.strategies.costFirst') }}</p>
              <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.recommendations.strategies.costFirstHint') }}</p>
            </div>
          </label>
          <label class="flex items-center space-x-3 cursor-pointer">
            <input
              v-model="strategy"
              type="radio"
              value="quality"
              @change="updateStrategy('quality')"
              class="form-check-input"
            >
            <div>
              <p class="text-sm" style="color: var(--od-text-primary)">{{ $t('cost.recommendations.strategies.qualityFirst') }}</p>
              <p class="text-xs" style="color: var(--od-text-muted)">{{ $t('cost.recommendations.strategies.qualityFirstHint') }}</p>
            </div>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'
import { useSimpleToast } from '@/composables/useSimpleToast'

const { t } = useI18n()
const costStore = useCostStore()
const { showSuccess } = useSimpleToast()

// 响应式数据
const strategy = ref('balanced')
const isUpdatingStrategy = ref(false)

// 模型数据
const models = ref([
  {
    name: 'GPT-4',
    inputPrice: 0.03,
    outputPrice: 0.06,
    quality: 5,
    speed: 3,
    recommended: true,
    recommendedFor: t('cost.recommendations.complex'),
    isCurrent: false
  },
  {
    name: 'GPT-3.5-Turbo',
    inputPrice: 0.001,
    outputPrice: 0.002,
    quality: 4,
    speed: 5,
    recommended: true,
    recommendedFor: t('cost.recommendations.general'),
    isCurrent: true
  },
  {
    name: 'DeepSeek-Chat',
    inputPrice: 0.0001,
    outputPrice: 0.0002,
    quality: 3,
    speed: 5,
    recommended: true,
    recommendedFor: t('cost.recommendations.simple'),
    isCurrent: false
  },
  {
    name: 'Claude-3',
    inputPrice: 0.015,
    outputPrice: 0.075,
    quality: 5,
    speed: 4,
    recommended: false,
    recommendedFor: '',
    isCurrent: false
  }
])

// 计算推荐
const recommendation = computed(() => {
  // 基于当前使用模式计算推荐
  const currentUsage = costStore.usageSummary?.model_breakdown || {}
  const totalCost = costStore.totalCost || 100
  
  // 如果主要使用GPT-4
  if (currentUsage['gpt-4']?.percentage > 50) {
    return {
      title: t('cost.recommendations.switchToGPT35'),
      description: t('cost.recommendations.switchToGPT35Desc'),
      savings: (totalCost * 0.7).toFixed(2)
    }
  }
  
  // 默认推荐
  return {
    title: t('cost.recommendations.optimizeUsage'),
    description: t('cost.recommendations.optimizeUsageDesc'),
    savings: (totalCost * 0.3).toFixed(2)
  }
})

// 应用推荐
const applyRecommendation = async () => {
  // 应用推荐的优化建议
  const suggestionId = 'use-gpt35-for-simple-tasks'
  try {
    await costStore.applyOptimizationSuggestion(suggestionId)
  } catch (error) {
    console.error('Failed to apply recommendation:', error)
  }
}

// 更新策略
const updateStrategy = async (newStrategy: string) => {
  if (isUpdatingStrategy.value) return
  
  isUpdatingStrategy.value = true
  try {
    await costStore.updateModelStrategy({
      strategy: newStrategy as 'balanced' | 'cost' | 'quality',
      rules: getStrategyRules(newStrategy),
      auto_switch: true
    })
    showSuccess(t('cost.recommendations.strategyUpdated'))
  } catch (error) {
    console.error('Failed to update strategy:', error)
  } finally {
    isUpdatingStrategy.value = false
  }
}

// 获取策略规则
const getStrategyRules = (strategyType: string) => {
  const rules: Record<string, any> = {
    balanced: {
      cost_weight: 0.5,
      quality_weight: 0.5,
      auto_fallback: true
    },
    cost: {
      prefer_gpt35: true,
      gpt4_threshold: 0.8,
      max_daily_cost: 10
    },
    quality: {
      prefer_gpt4: true,
      min_quality_score: 0.8,
      allow_cost_override: true
    }
  }
  return rules[strategyType] || rules.balanced
}

// 初始化
onMounted(async () => {
  // 获取模型定价信息和当前策略
  await Promise.all([
    costStore.fetchModelPricing(),
    costStore.fetchModelStrategy()
  ])
  
  // 设置当前策略
  if (costStore.modelStrategy) {
    strategy.value = costStore.modelStrategy.strategy
  }
  
  // 更新模型数据
  if (costStore.modelPricing.length > 0) {
    models.value = costStore.modelPricing.map(m => ({
      name: m.name,
      inputPrice: m.input_price,
      outputPrice: m.output_price,
      quality: getModelQuality(m.name),
      speed: getModelSpeed(m.name),
      recommended: true,
      recommendedFor: getRecommendedFor(m.name),
      isCurrent: isCurrentModel(m.name)
    }))
  }
})

// 移除 watch，因为我们现在使用 @change 事件

// 辅助函数
const getModelQuality = (name: string) => {
  const qualityMap: Record<string, number> = {
    'gpt-4': 5,
    'gpt-3.5-turbo': 4,
    'deepseek-chat': 3,
    'claude': 5
  }
  return qualityMap[name.toLowerCase()] || 3
}

const getModelSpeed = (name: string) => {
  const speedMap: Record<string, number> = {
    'gpt-4': 3,
    'gpt-3.5-turbo': 5,
    'deepseek-chat': 5,
    'claude': 4
  }
  return speedMap[name.toLowerCase()] || 3
}

const getRecommendedFor = (name: string) => {
  const map: Record<string, string> = {
    'gpt-4': t('cost.recommendations.complex'),
    'gpt-3.5-turbo': t('cost.recommendations.general'),
    'deepseek-chat': t('cost.recommendations.simple')
  }
  return map[name.toLowerCase()] || ''
}

const isCurrentModel = (name: string) => {
  // 检查是否是当前主要使用的模型
  const breakdown = costStore.usageSummary?.model_breakdown || {}
  const modelUsage = breakdown[name]
  return modelUsage && modelUsage.percentage > 40
}
</script>