<template>
  <div class="card--od--refined p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold" style="color: var(--od-text-primary)">{{ $t('cost.breakdown.title') }}</h2>
      <select
        v-model="timeRange"
        class="input--od input--od--sm"
        @change="refreshData"
      >
        <option value="today">{{ $t('cost.breakdown.today') }}</option>
        <option value="yesterday">{{ $t('cost.breakdown.yesterday') }}</option>
        <option value="week">{{ $t('cost.breakdown.thisWeek') }}</option>
        <option value="month">{{ $t('cost.breakdown.thisMonth') }}</option>
      </select>
    </div>
    
    <!-- 按模型分解 -->
    <div class="mb-8">
      <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.breakdown.byModel') }}</h3>
      <div class="space-y-3">
        <div 
          v-for="model in modelBreakdown" 
          :key="model.name"
          class="card--od p-4" style="background: var(--od-bg-secondary)"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center space-x-3">
              <div 
                class="w-3 h-3 rounded-full"
                :style="{ backgroundColor: model.color }"
              ></div>
              <span class="font-medium" style="color: var(--od-text-primary)">{{ model.name }}</span>
            </div>
            <div class="text-right">
              <p class="font-medium" style="color: var(--od-text-primary)">${{ model.cost.toFixed(2) }}</p>
              <p class="text-xs" style="color: var(--od-text-muted)">{{ formatNumber(model.tokens) }} tokens</p>
            </div>
          </div>
          <div class="w-full rounded-full h-2" style="background: var(--od-bg-primary)">
            <div 
              class="h-2 rounded-full transition-all duration-300"
              :style="{ 
                width: `${model.percentage}%`,
                backgroundColor: model.color 
              }"
            ></div>
          </div>
          <div class="flex justify-between mt-2 text-xs" style="color: var(--od-text-muted)">
            <span>{{ model.percentage.toFixed(1) }}%</span>
            <span>${{ (model.cost / model.tokens * 1000).toFixed(4) }}/1K tokens</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 按功能分解 -->
    <div class="mb-8">
      <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.breakdown.byFeature') }}</h3>
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="feature in featureBreakdown"
          :key="feature.name"
          class="card--od p-4" style="background: var(--od-bg-secondary)"
        >
          <div class="flex items-center justify-between mb-2">
            <span style="color: var(--od-text-secondary)">{{ feature.name }}</span>
            <span class="font-medium" style="color: var(--od-text-primary)">${{ feature.cost.toFixed(2) }}</span>
          </div>
          <div class="text-xs" style="color: var(--od-text-muted)">
            {{ feature.count }} {{ $t('cost.breakdown.requests') }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- 成本趋势 -->
    <div>
      <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.breakdown.trend') }}</h3>
      <div class="h-64">
        <canvas ref="trendChart"></canvas>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'
import Chart from 'chart.js/auto'

const { t } = useI18n()
const costStore = useCostStore()

// 响应式数据
const timeRange = ref('today')
const trendChart = ref<HTMLCanvasElement>()
let chartInstance: Chart | null = null

// 计算属性
const modelBreakdown = computed(() => {
  const breakdown = costStore.usageSummary?.model_breakdown || {}
  const total = Object.values(breakdown).reduce((sum, data) => sum + (data.cost || 0), 0)
  
  return Object.entries(breakdown).map(([name, data]) => ({
    name,
    cost: data.cost || 0,
    tokens: data.tokens || 0,
    percentage: total > 0 ? ((data.cost || 0) / total) * 100 : 0,
    color: getModelColor(name)
  })).sort((a, b) => b.cost - a.cost)
})

const featureBreakdown = computed(() => {
  // 这里应该从后端获取，暂时使用模拟数据
  return [
    { name: t('cost.breakdown.features.analysis'), cost: 12.5, count: 25 },
    { name: t('cost.breakdown.features.chat'), cost: 8.3, count: 156 },
    { name: t('cost.breakdown.features.research'), cost: 15.7, count: 12 },
    { name: t('cost.breakdown.features.tools'), cost: 4.2, count: 89 }
  ]
})

// 方法
const getModelColor = (model: string) => {
  const colors: Record<string, string> = {
    'gpt-4': '#3B82F6',
    'gpt-3.5-turbo': '#10B981',
    'deepseek-chat': '#8B5CF6',
    'claude': '#F59E0B'
  }
  for (const [key, color] of Object.entries(colors)) {
    if (model.toLowerCase().includes(key)) return color
  }
  return '#6B7280'
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const refreshData = async () => {
  // 根据时间范围刷新数据
  const days = timeRange.value === 'today' ? 1 :
               timeRange.value === 'yesterday' ? 1 :
               timeRange.value === 'week' ? 7 : 30
  
  await costStore.fetchUsageSummary(days)
  updateChart()
}

const initChart = () => {
  if (!trendChart.value) return
  
  const ctx = trendChart.value.getContext('2d')
  if (!ctx) return
  
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: t('cost.breakdown.dailyCost'),
        data: [],
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'var(--od-bg-secondary)',
          titleColor: 'var(--od-text-primary)',
          bodyColor: 'var(--od-text-secondary)',
          borderColor: 'var(--od-border)',
          borderWidth: 1,
          cornerRadius: 8,
          padding: 12,
          displayColors: false,
          callbacks: {
            label: (context) => `$${context.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: {
          grid: {
            color: 'var(--od-border)',
            display: true
          },
          ticks: {
            color: 'var(--od-text-muted)'
          }
        },
        y: {
          grid: {
            color: 'var(--od-border)',
            display: true
          },
          ticks: {
            color: 'var(--od-text-muted)',
            callback: (value) => `$${value}`
          }
        }
      }
    }
  })
  
  updateChart()
}

const updateChart = () => {
  if (!chartInstance) return
  
  // 获取趋势数据
  const trend = costStore.getCostTrend(timeRange.value === 'month' ? 30 : 7)
  const dates = Object.keys(trend).sort()
  const values = dates.map(date => trend[date])
  
  chartInstance.data.labels = dates.map(date => {
    const d = new Date(date)
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  })
  chartInstance.data.datasets[0].data = values
  chartInstance.update()
}

// 生命周期
onMounted(() => {
  initChart()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})

// 监听数据变化
watch(() => costStore.costHistory, () => {
  updateChart()
})
</script>