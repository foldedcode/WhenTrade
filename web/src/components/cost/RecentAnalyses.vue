<template>
  <div class="card--od--refined p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-semibold" style="color: var(--od-text-primary)">{{ t('common.recentAnalysis') }}</h2>
      <span class="text-sm" style="color: var(--od-text-muted)">{{ t('cost.realtimeTracking') }}</span>
    </div>
    
    <div class="space-y-3">
      <div
        v-for="history in recentAnalyses"
        :key="history.id"
        class="cursor-pointer p-4 rounded-lg transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
        style="background: var(--od-bg-secondary); border: 1px solid var(--od-border)"
        @click="handleAnalysisClick(history)"
      >
        <div class="flex justify-between items-start mb-2">
          <div class="flex items-center space-x-2">
            <div class="text-sm font-medium" style="color: var(--od-text-primary)">
              {{ history.config.symbol }}
            </div>
            <div class="text-xs px-2 py-1 rounded" 
                 :style="{ 
                   background: getMarketTypeColor(history.config.marketType), 
                   color: '#ffffff'
                 }">
              {{ getMarketTypeLabel(history.config.marketType) }}
            </div>
            <div class="text-xs px-2 py-1 rounded"
                 :style="{ 
                   background: getDepthColor(history.config.depth),
                   color: '#ffffff'
                 }">
              {{ t('cost.recent.depth') }} {{ history.config.depth }}
            </div>
          </div>
          <div class="text-xs" style="color: var(--od-text-muted)">
            {{ formatTimeAgo(history.timestamp) }}
          </div>
        </div>
        
        <div class="flex justify-between items-center">
          <div class="text-sm" style="color: var(--od-text-secondary)">
            {{ getMarketTypeLabel(history.config.marketType) }} • 
            {{ t('cost.recent.depth') }} {{ history.config.depth }}
          </div>
          <div class="flex items-center space-x-3">
            <div class="text-right">
              <div class="text-sm font-medium" style="color: var(--od-color-success)">
                ${{ (history.cost || 0).toFixed(3) }}
              </div>
              <div class="text-xs" style="color: var(--od-text-muted)">
                {{ formatDuration(history.duration) }}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 空状态 -->
      <div v-if="recentAnalyses.length === 0" class="text-center py-8">
        <div class="text-4xl mb-2">📊</div>
        <div class="text-sm" style="color: var(--od-text-muted)">
          {{ t('table.noData') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAnalysisStore } from '@/stores/analysis'
import type { AnalysisHistory } from '@/types/analysis'

const router = useRouter()
const { t } = useI18n()
const analysisStore = useAnalysisStore()

// 获取最近的分析记录（限制5条）
const recentAnalyses = computed(() => {
  return analysisStore.analysisHistory.slice(0, 5)
})

// 处理分析记录点击
const handleAnalysisClick = (history: AnalysisHistory) => {
  // 跳转到主页并传递历史记录数据
  router.push({
    path: '/',
    query: {
      showHistory: 'true',
      historyId: history.id
    }
  })
}

// 格式化时间差
const formatTimeAgo = (timestamp: number): string => {
  const now = Date.now()
  const diff = now - timestamp
  const minutes = Math.floor(diff / (1000 * 60))
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days > 0) return t('time.daysAgo', { count: days })
  if (hours > 0) return t('time.hoursAgo', { count: hours })
  if (minutes > 0) return t('time.minutesAgo', { count: minutes })
  return t('time.justNow')
}

// 格式化持续时间
const formatDuration = (duration: number): string => {
  const seconds = Math.floor(duration / 1000)
  if (seconds < 60) return t('time.seconds', { count: seconds })
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return t('time.minutesSeconds', { minutes, seconds: remainingSeconds })
}

// 获取市场类型标签
const getMarketTypeLabel = (type: string | undefined): string => {
  if (!type) return t('marketTypes.unknown')
  return t(`marketTypes.${type}`, type)
}

// 获取市场类型颜色
const getMarketTypeColor = (type: string | undefined): string => {
  if (!type) return '#6b7280'
  const colors: Record<string, string> = {
    crypto: '#f59e0b'  // 橙色
  }
  return colors[type] || '#6b7280'
}

// 获取深度颜色
const getDepthColor = (depth: number): string => {
  if (depth === 1) return '#10b981' // 绿色 - 基础
  if (depth === 2) return '#3b82f6' // 蓝色 - 标准
  if (depth === 3) return '#8b5cf6' // 紫色 - 深入
  return '#6b7280' // 默认灰色
}
</script>

<style scoped>
/* 悬停效果 */
.cursor-pointer:hover {
  transform: translateY(-1px);
}

/* 动画过渡 */
.cursor-pointer {
  transition: all 0.2s ease-in-out;
}
</style>