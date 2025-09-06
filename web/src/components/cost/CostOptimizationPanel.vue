<template>
  <div class="card--od--refined p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-semibold" style="color: var(--od-text-primary)">{{ $t('cost.optimization.title') }}</h2>
      <div class="flex items-center space-x-3">
        <!-- 影响程度筛选 -->
        <select
          v-model="selectedImpact"
          class="input--od input--od--sm"
          @change="filterSuggestions"
        >
          <option value="all">{{ $t('cost.optimization.allImpacts') }}</option>
          <option value="high">{{ $t('cost.optimization.impacts.high') }}</option>
          <option value="medium">{{ $t('cost.optimization.impacts.medium') }}</option>
          <option value="low">{{ $t('cost.optimization.impacts.low') }}</option>
        </select>

        <!-- 刷新建议 -->
        <button
          @click="refreshSuggestions"
          class="btn--od btn--od--primary btn--od--sm"
          :disabled="isRefreshing"
        >
          <svg v-if="isRefreshing" class="w-4 h-4 animate-spin mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ $t('cost.optimization.refresh') }}
        </button>
      </div>
    </div>

    <!-- 总体节省潜力 -->
    <div class="card--od--refined p-4 mb-6" style="border-color: var(--od-color-success); background: rgba(var(--od-color-success-rgb), 0.1)">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-base font-semibold" style="color: var(--od-text-primary)">{{ $t('cost.optimization.totalSavingsPotential') }}</h3>
          <p class="text-sm" style="color: var(--od-text-secondary)">{{ $t('cost.optimization.implementAllSuggestions') }}</p>
        </div>
        <div class="text-right">
          <p class="text-2xl font-bold" style="color: var(--od-color-success)">${{ totalSavingsPotential.toFixed(2) }}</p>
          <p class="text-sm" style="color: var(--od-text-secondary)">{{ totalSavingsPercentage }}% {{ $t('cost.optimization.reduction') }}</p>
        </div>
      </div>
    </div>

    <!-- 优化建议列表 -->
    <div class="space-y-4">
      <div
        v-for="suggestion in filteredSuggestions"
        :key="suggestion.id"
        class="card--od--refined card--od--interactive p-5"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <!-- 标题和图标 -->
            <div class="flex items-center space-x-3 mb-3">
              <div class="text-2xl">{{ suggestion.icon }}</div>
              <div>
                <h3 class="text-base font-semibold" style="color: var(--od-text-primary)">{{ suggestion.title }}</h3>
                <p class="text-sm" style="color: var(--od-text-secondary)">{{ suggestion.category }}</p>
              </div>
            </div>

            <!-- 描述 -->
            <p class="mb-4" style="color: var(--od-text-secondary)">{{ suggestion.description }}</p>

            <!-- 标签 -->
            <div class="flex items-center space-x-2 mb-4">
              <!-- 影响程度 -->
              <span 
                class="px-2 py-1 rounded-full text-xs font-medium"
                :class="getImpactClass(getDifficultyAsImpact(suggestion.difficulty))"
              >
                {{ $t(`cost.optimization.impacts.${getDifficultyAsImpact(suggestion.difficulty)}`) }}
              </span>

              <!-- 难度等级 -->
              <span 
                class="px-2 py-1 rounded-full text-xs font-medium"
                :class="getDifficultyClass(suggestion.difficulty)"
              >
                {{ $t(`cost.optimization.difficulty.${suggestion.difficulty}`) }}
              </span>

              <!-- 实施时间 -->
              <span class="px-2 py-1 rounded-full text-xs" style="background: var(--od-bg-secondary); color: var(--od-text-secondary)">
                <svg class="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {{ suggestion.implementationTime }}
              </span>

              <!-- 已实施标记 -->
              <span 
                v-if="suggestion.is_implemented" 
                class="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs flex items-center"
              >
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                {{ $t('cost.optimization.implemented') }}
              </span>
            </div>

            <!-- 潜在节省 -->
            <div class="card--od p-3 mb-4" style="background: var(--od-bg-secondary)">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div class="text-center">
                  <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.optimization.potentialSavings') }}</p>
                  <p class="text-lg font-bold" style="color: var(--od-color-success)">${{ suggestion.potential_savings.toFixed(2) }}</p>
                </div>
                <div class="text-center">
                  <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.optimization.percentage') }}</p>
                  <p class="text-lg font-bold" style="color: var(--od-color-success)">{{ Math.round((suggestion.potential_savings / (costStore.totalCost || 100)) * 100) }}%</p>
                </div>
                <div class="text-center">
                  <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.optimization.timeframe') }}</p>
                  <p class="text-lg font-bold" style="color: var(--od-color-primary)">{{ $t('cost.optimization.timeframes.monthly') }}</p>
                </div>
              </div>
            </div>

            <!-- 实施步骤 -->
            <div v-if="expandedSuggestion === suggestion.id" class="mb-4">
              <h4 class="text-sm font-semibold text-white mb-2">{{ $t('cost.optimization.implementationSteps') }}</h4>
              <ol class="space-y-2">
                <li 
                  v-for="(step, index) in suggestion.steps"
                  :key="index"
                  class="flex items-start space-x-2 text-sm text-slate-300"
                >
                  <span class="w-5 h-5 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                    {{ index + 1 }}
                  </span>
                  <span>{{ step }}</span>
                </li>
              </ol>
            </div>

            <!-- 操作按钮 -->
            <div class="flex items-center space-x-3">
              <!-- 展开/收起详情 -->
              <button
                @click="toggleSuggestionDetails(suggestion.id)"
                class="btn--od btn--od--ghost btn--od--sm"
              >
                {{ expandedSuggestion === suggestion.id ? $t('cost.optimization.hideDetails') : $t('cost.optimization.showDetails') }}
              </button>

              <!-- 实施建议 -->
              <button
                v-if="!suggestion.is_implemented"
                @click="implementSuggestion(suggestion.id)"
                class="btn--od btn--od--success btn--od--sm"
                :disabled="isImplementing"
              >
                <svg v-if="isImplementing" class="w-3 h-3 animate-spin mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {{ $t('cost.optimization.implement') }}
              </button>

              <!-- 忽略建议 -->
              <button
                v-if="!suggestion.is_implemented"
                @click="ignoreSuggestion(suggestion.id)"
                class="btn--od btn--od--ghost btn--od--sm"
              >
                {{ $t('cost.optimization.ignore') }}
              </button>

              <!-- 分享建议 -->
              <button
                @click="shareSuggestion(suggestion.id)"
                class="btn--od btn--od--ghost btn--od--sm"
              >
                <svg class="w-3 h-3 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
                </svg>
                {{ $t('cost.optimization.share') }}
              </button>
            </div>
          </div>
        </div>

        <!-- 实施时间线（如果已实施） -->
        <div v-if="suggestion.is_implemented" class="mt-4 pt-4 border-t border-slate-600">
          <div class="flex items-center space-x-2 text-sm text-green-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ $t('cost.optimization.implementedOn') }} {{ formatDate(suggestion.implementedAt) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredSuggestions.length === 0" class="text-center py-12">
      <div class="text-6xl mb-4">🎯</div>
      <h3 class="text-lg font-semibold text-white mb-2">{{ $t('cost.optimization.noSuggestions') }}</h3>
      <p class="text-slate-400 mb-4">{{ $t('cost.optimization.allOptimized') }}</p>
      <button
        @click="refreshSuggestions"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
      >
        {{ $t('cost.optimization.checkAgain') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'
import { useGamificationStore } from '@/stores/gamification'

const { t } = useI18n()
const costStore = useCostStore()
const gamificationStore = useGamificationStore()

// 响应式数据
const selectedImpact = ref('all')
const expandedSuggestion = ref<string | null>(null)
const isRefreshing = ref(false)
const isImplementing = ref(false)

// 计算属性
const filteredSuggestions = computed(() => {
  const suggestions = costStore.optimizationSuggestions.map(s => ({
    ...s,
    icon: getIconForSuggestion(s.id),
    category: getCategoryForSuggestion(s.id),
    implementationTime: getImplementationTime(s.difficulty),
    steps: getImplementationSteps(s.id)
  }))
  
  if (selectedImpact.value === 'all') {
    return suggestions
  }
  // 根据难度映射影响程度
  return suggestions.filter(s => {
    const impactMap = { easy: 'low', medium: 'medium', hard: 'high' }
    return impactMap[s.difficulty] === selectedImpact.value
  })
})

const totalSavingsPotential = computed(() => {
  return filteredSuggestions.value
    .filter(s => !s.is_implemented)
    .reduce((total, s) => total + s.potential_savings, 0)
})

const totalSavingsPercentage = computed(() => {
  const unimplemented = filteredSuggestions.value.filter(s => !s.is_implemented)
  if (unimplemented.length === 0) return 0
  
  // 估算百分比：潜在节省 / 当前总成本 * 100
  const currentCost = costStore.totalCost || 100
  const totalSavings = unimplemented.reduce((sum, s) => sum + s.potential_savings, 0)
  return Math.round((totalSavings / currentCost) * 100)
})

// 方法
const getImpactClass = (impact: string) => {
  const classes = {
    high: 'bg-red-500/20 text-red-400',
    medium: 'bg-yellow-500/20 text-yellow-400', 
    low: 'bg-green-500/20 text-green-400'
  }
  return classes[impact as keyof typeof classes] || classes.low
}

const getDifficultyClass = (difficulty: string) => {
  const classes = {
    easy: 'bg-green-500/20 text-green-400',
    medium: 'bg-yellow-500/20 text-yellow-400',
    hard: 'bg-red-500/20 text-red-400'
  }
  return classes[difficulty as keyof typeof classes] || classes.medium
}

// 将难度映射为影响程度
const getDifficultyAsImpact = (difficulty: string): string => {
  const map = { easy: 'low', medium: 'medium', hard: 'high' }
  return map[difficulty as keyof typeof map] || 'medium'
}

const toggleSuggestionDetails = (suggestionId: string) => {
  expandedSuggestion.value = expandedSuggestion.value === suggestionId ? null : suggestionId
}

// 辅助函数
const getIconForSuggestion = (id: string) => {
  const iconMap: Record<string, string> = {
    'use-gpt35-for-simple-tasks': '🎯',
    'batch-processing': '📦',
    'enable-caching': '💾'
  }
  return iconMap[id] || '💡'
}

const getCategoryForSuggestion = (id: string) => {
  const categoryMap: Record<string, string> = {
    'use-gpt35-for-simple-tasks': t('cost.optimization.categories.modelSelection'),
    'batch-processing': t('cost.optimization.categories.apiOptimization'),
    'enable-caching': t('cost.optimization.categories.performance')
  }
  return categoryMap[id] || t('cost.optimization.categories.general')
}

const getImplementationTime = (difficulty: string) => {
  const timeMap: Record<string, string> = {
    easy: '< 5 ' + t('cost.optimization.minutes'),
    medium: '15-30 ' + t('cost.optimization.minutes'),
    hard: '1-2 ' + t('cost.optimization.hours')
  }
  return timeMap[difficulty] || '30 ' + t('cost.optimization.minutes')
}

const getImplementationSteps = (id: string) => {
  const stepsMap: Record<string, string[]> = {
    'use-gpt35-for-simple-tasks': [
      t('cost.optimization.steps.analyzeUsage'),
      t('cost.optimization.steps.identifySimpleTasks'),
      t('cost.optimization.steps.updateModelStrategy'),
      t('cost.optimization.steps.monitorPerformance')
    ],
    'batch-processing': [
      t('cost.optimization.steps.groupRequests'),
      t('cost.optimization.steps.implementBatching'),
      t('cost.optimization.steps.testBatchSize'),
      t('cost.optimization.steps.deployChanges')
    ],
    'enable-caching': [
      t('cost.optimization.steps.identifyCacheable'),
      t('cost.optimization.steps.setupCache'),
      t('cost.optimization.steps.configureTTL'),
      t('cost.optimization.steps.verifyCaching')
    ]
  }
  return stepsMap[id] || [t('cost.optimization.steps.default')]
}

const implementSuggestion = async (suggestionId: string) => {
  isImplementing.value = true
  try {
    // 使用新的自动应用API
    await costStore.applyOptimizationSuggestion(suggestionId)
    
    // 显示成功通知
    gamificationStore.addNotification({
      type: 'achievement_unlocked',
      title: t('cost.notifications.optimizationImplemented.title'),
      message: t('cost.notifications.optimizationImplemented.message'),
      icon: '💡',
      color: '#10B981'
    })
  } finally {
    isImplementing.value = false
  }
}

const ignoreSuggestion = (suggestionId: string) => {
  // 标记为已忽略（将来可以添加API调用）
  const suggestion = costStore.optimizationSuggestions.find(s => s.id === suggestionId)
  if (suggestion) {
    suggestion.is_implemented = true  // 暂时标记为已实施
  }
  
  // 隐藏详情
  expandedSuggestion.value = null
}

const shareSuggestion = (suggestionId: string) => {
  const suggestion = costStore.optimizationSuggestions.find(s => s.id === suggestionId)
  if (!suggestion) return

  const percentage = Math.round((suggestion.potential_savings / (costStore.totalCost || 100)) * 100)
  const shareText = t('cost.notifications.suggestionShared.shareTemplate', {
    title: suggestion.title,
    amount: suggestion.potential_savings.toFixed(2),
    percentage: percentage,
    description: suggestion.description
  })
  
  if (navigator.share) {
    navigator.share({
      title: t('cost.notifications.suggestionShared.title'),
      text: shareText
    })
  } else {
    // 复制到剪贴板
    navigator.clipboard.writeText(shareText)
    gamificationStore.addNotification({
      type: 'achievement_unlocked',
      title: t('cost.notifications.copiedToClipboard.title'),
      message: t('cost.notifications.copiedToClipboard.message'),
      icon: '📋',
      color: '#3B82F6'
    })
  }
}

const refreshSuggestions = async () => {
  isRefreshing.value = true
  try {
    // 获取真实的优化建议
    await costStore.fetchOptimizationSuggestions()
    
    // 重置筛选
    selectedImpact.value = 'all'
    expandedSuggestion.value = null
  } finally {
    isRefreshing.value = false
  }
}

const filterSuggestions = () => {
  expandedSuggestion.value = null
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 初始化时加载数据
onMounted(async () => {
  if (costStore.optimizationSuggestions.length === 0) {
    await refreshSuggestions()
  }
})
</script> 