<template>
  <div class="card--od--refined p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold" style="color: var(--od-text-primary)">{{ $t('cost.tokenUsage.title') }}</h2>
      <div class="flex items-center space-x-3">
        <!-- 时间范围选择 -->
        <select
          v-model="selectedTimeframe"
          class="input--od input--od--sm"
          @change="updateChartData"
        >
          <option value="1h">{{ $t('cost.tokenUsage.timeframes.1h') }}</option>
          <option value="24h">{{ $t('cost.tokenUsage.timeframes.24h') }}</option>
          <option value="7d">{{ $t('cost.tokenUsage.timeframes.7d') }}</option>
          <option value="30d">{{ $t('cost.tokenUsage.timeframes.30d') }}</option>
        </select>
        
        <!-- 模型筛选 -->
        <select
          v-model="selectedModel"
          class="input--od input--od--sm"
          @change="updateChartData"
        >
          <option value="all">{{ $t('cost.tokenUsage.allModels') }}</option>
          <option value="gpt-4o-mini">GPT-4O Mini</option>
          <option value="gpt-4o">GPT-4O</option>
          <option value="claude-3-sonnet">Claude 3 Sonnet</option>
          <option value="claude-3-haiku">Claude 3 Haiku</option>
        </select>

        <!-- 刷新按钮 -->
        <button
          @click="refreshData"
          class="p-2 transition-colors hover:opacity-80"
          style="color: var(--od-text-muted)"
          :disabled="isLoading"
        >
          <svg class="w-4 h-4" :class="{ 'animate-spin': isLoading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 实时统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <!-- 总Token使用量 -->
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.tokenUsage.totalTokens') }}</p>
            <p class="text-2xl font-bold" style="color: var(--od-text-primary)">{{ formatNumber(totalTokens) }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg flex items-center justify-center" style="background: rgba(var(--od-color-primary-rgb), 0.2)">
            <svg class="w-6 h-6" style="color: var(--od-color-primary)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
        <div class="mt-2 flex items-center">
          <span class="text-xs" :style="{ color: tokenTrend >= 0 ? 'var(--od-color-error)' : 'var(--od-color-success)' }">
            {{ tokenTrend >= 0 ? '↑' : '↓' }} {{ Math.abs(tokenTrend) }}%
          </span>
          <span class="text-xs ml-1" style="color: var(--od-text-muted)">{{ $t('cost.tokenUsage.vsLastPeriod') }}</span>
        </div>
      </div>

      <!-- 输入Token -->
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.tokenUsage.inputTokens') }}</p>
            <p class="text-2xl font-bold" style="color: var(--od-text-primary)">{{ formatNumber(inputTokens) }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg flex items-center justify-center" style="background: rgba(var(--od-color-success-rgb), 0.2)">
            <svg class="w-6 h-6" style="color: var(--od-color-success)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16l-4-4m0 0l4-4m-4 4h18" />
            </svg>
          </div>
        </div>
        <div class="mt-2">
          <span class="text-xs" style="color: var(--od-text-muted)">{{ ((inputTokens / totalTokens) * 100).toFixed(1) }}% {{ $t('cost.tokenUsage.ofTotal') }}</span>
        </div>
      </div>

      <!-- 输出Token -->
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.tokenUsage.outputTokens') }}</p>
            <p class="text-2xl font-bold" style="color: var(--od-text-primary)">{{ formatNumber(outputTokens) }}</p>
          </div>
          <div class="w-12 h-12 rounded-lg flex items-center justify-center" style="background: rgba(var(--od-color-secondary-rgb), 0.2)">
            <svg class="w-6 h-6" style="color: var(--od-color-secondary)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </div>
        </div>
        <div class="mt-2">
          <span class="text-xs" style="color: var(--od-text-muted)">{{ ((outputTokens / totalTokens) * 100).toFixed(1) }}% {{ $t('cost.tokenUsage.ofTotal') }}</span>
        </div>
      </div>

      <!-- 平均效率 -->
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('cost.tokenUsage.efficiency') }}</p>
            <p class="text-2xl font-bold" style="color: var(--od-text-primary)">{{ averageEfficiency }}%</p>
          </div>
          <div class="w-12 h-12 rounded-lg flex items-center justify-center" style="background: rgba(var(--od-color-warning-rgb), 0.2)">
            <svg class="w-6 h-6" style="color: var(--od-color-warning)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
        <div class="mt-2">
          <span class="text-xs" :style="{ color: efficiencyTrend >= 0 ? 'var(--od-color-success)' : 'var(--od-color-error)' }">
            {{ efficiencyTrend >= 0 ? '↑' : '↓' }} {{ Math.abs(efficiencyTrend) }}%
          </span>
          <span class="text-xs ml-1" style="color: var(--od-text-muted)">{{ $t('cost.tokenUsage.vsLastPeriod') }}</span>
        </div>
      </div>
    </div>

    <!-- Token使用趋势图表 -->
    <div class="card--od p-4 mb-6" style="background: var(--od-bg-secondary)">
      <h3 class="text-lg font-semibold mb-4" style="color: var(--od-text-primary)">{{ $t('cost.tokenUsage.usageTrend') }}</h3>
      <div class="h-64 relative">
        <canvas ref="chartCanvas" class="w-full h-full"></canvas>
      </div>
    </div>

    <!-- 模型使用分布 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 按模型分布 -->
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <h3 class="text-lg font-semibold mb-4" style="color: var(--od-text-primary)">{{ $t('cost.tokenUsage.modelDistribution') }}</h3>
        <div class="space-y-3">
          <div
            v-for="model in modelDistribution"
            :key="model.name"
            class="flex items-center justify-between"
          >
            <div class="flex items-center space-x-3">
              <div 
                class="w-4 h-4 rounded-full"
                :style="{ backgroundColor: model.color }"
              ></div>
              <span class="text-sm" style="color: var(--od-text-secondary)">{{ model.name }}</span>
            </div>
            <div class="flex items-center space-x-2">
              <div class="w-24 rounded-full h-2" style="background: var(--od-bg-primary)">
                <div 
                  class="h-2 rounded-full transition-all duration-300"
                  :style="{ width: `${model.percentage}%`, backgroundColor: model.color }"
                ></div>
              </div>
              <span class="text-sm font-medium w-12 text-right" style="color: var(--od-text-primary)">{{ model.percentage }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Token效率排行 -->
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <h3 class="text-lg font-semibold mb-4" style="color: var(--od-text-primary)">{{ $t('cost.tokenUsage.efficiencyRanking') }}</h3>
        <div class="space-y-3">
          <div
            v-for="(item, index) in efficiencyRanking"
            :key="item.model"
            class="flex items-center justify-between p-2 rounded-lg" style="background: var(--od-bg-primary)"
          >
            <div class="flex items-center space-x-3">
              <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style="background: var(--od-bg-secondary); color: var(--od-text-primary)">
                {{ index + 1 }}
              </div>
              <span class="text-sm" style="color: var(--od-text-secondary)">{{ item.model }}</span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="text-sm" style="color: var(--od-text-primary)">{{ item.efficiency }}%</span>
              <span class="text-xs" style="color: var(--od-text-muted)">{{ formatNumber(item.tokens) }} tokens</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'

const { t } = useI18n()
const costStore = useCostStore()

// 响应式数据
const isLoading = ref(false)
const selectedTimeframe = ref('24h')
const selectedModel = ref('all')
const chartCanvas = ref<HTMLCanvasElement>()

// Token统计数据 - 从store获取
const totalTokens = computed(() => costStore.usageSummary?.total_tokens || 0)
const inputTokens = computed(() => {
  // 计算所有模型的输入token总和
  if (!costStore.usageDetails.length) return 0
  return costStore.usageDetails.reduce((sum, d) => sum + d.input_tokens, 0)
})
const outputTokens = computed(() => {
  // 计算所有模型的输出token总和
  if (!costStore.usageDetails.length) return 0
  return costStore.usageDetails.reduce((sum, d) => sum + d.output_tokens, 0)
})
const averageEfficiency = ref(87)
const tokenTrend = ref(12.5)
const efficiencyTrend = ref(3.2)

// 模型分布数据 - 从store计算
const modelDistribution = computed(() => {
  const breakdown = costStore.usageSummary?.model_breakdown || {}
  const models = Object.entries(breakdown).map(([name, data]) => ({
    name,
    percentage: data.percentage || 0,
    color: getModelColor(name),
    tokens: data.tokens || 0
  }))
  return models.sort((a, b) => b.percentage - a.percentage)
})

// 根据模型名称获取颜色
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

// 效率排行数据
const efficiencyRanking = ref([
  { model: 'Claude 3 Haiku', efficiency: 94, tokens: 11326 },
  { model: 'GPT-4O Mini', efficiency: 89, tokens: 56628 },
  { model: 'Claude 3 Sonnet', efficiency: 85, tokens: 35235 },
  { model: 'GPT-4O', efficiency: 82, tokens: 22651 }
])

// Chart.js 实例
let chartInstance: any = null

// 计算属性
const chartData = computed(() => {
  // 根据选择的时间范围生成模拟数据
  const dataPoints = getDataPointsForTimeframe(selectedTimeframe.value)
  return {
    labels: dataPoints.map(p => p.label),
    datasets: [
      {
        label: t('cost.tokenUsage.inputTokens'),
        data: dataPoints.map(p => p.input),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: t('cost.tokenUsage.outputTokens'),
        data: dataPoints.map(p => p.output),
        borderColor: '#8B5CF6',
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  }
})

// 方法
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const getDataPointsForTimeframe = (timeframe: string) => {
  const now = new Date()
  const points = []
  
  switch (timeframe) {
    case '1h':
      for (let i = 11; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 5 * 60 * 1000)
        points.push({
          label: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          input: Math.floor(Math.random() * 1000) + 500,
          output: Math.floor(Math.random() * 600) + 300
        })
      }
      break
    case '24h':
      for (let i = 23; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 60 * 60 * 1000)
        points.push({
          label: time.toLocaleTimeString([], { hour: '2-digit' }) + ':00',
          input: Math.floor(Math.random() * 5000) + 2000,
          output: Math.floor(Math.random() * 3000) + 1500
        })
      }
      break
    case '7d':
      for (let i = 6; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
        points.push({
          label: time.toLocaleDateString([], { weekday: 'short' }),
          input: Math.floor(Math.random() * 20000) + 10000,
          output: Math.floor(Math.random() * 15000) + 8000
        })
      }
      break
    case '30d':
      for (let i = 29; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
        points.push({
          label: time.toLocaleDateString([], { month: 'short', day: 'numeric' }),
          input: Math.floor(Math.random() * 50000) + 30000,
          output: Math.floor(Math.random() * 30000) + 20000
        })
      }
      break
  }
  
  return points
}

const initChart = async () => {
  if (!chartCanvas.value) return

  // 动态导入 Chart.js
  const { Chart, registerables } = await import('chart.js')
  Chart.register(...registerables)

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: chartData.value,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: 'var(--od-text-primary)'
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: 'var(--od-text-muted)'
          },
          grid: {
            color: 'var(--od-border)'
          }
        },
        y: {
          ticks: {
            color: 'var(--od-text-muted)',
            callback: function(value: any) {
              return formatNumber(value)
            }
          },
          grid: {
            color: 'var(--od-border)'
          }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      },
      elements: {
        point: {
          radius: 3,
          hoverRadius: 6
        }
      }
    }
  })
}

const updateChartData = () => {
  if (chartInstance) {
    chartInstance.data = chartData.value
    chartInstance.update()
  }
}

const refreshData = async () => {
  isLoading.value = true
  try {
    // 获取真实数据
    const days = selectedTimeframe.value === '1h' ? 1 : 
                selectedTimeframe.value === '24h' ? 1 :
                selectedTimeframe.value === '7d' ? 7 : 30
    await costStore.fetchUsageSummary(days)
    await costStore.fetchUsageDetails({ limit: 100 })
    
    // 更新趋势数据（computed属性会自动从store更新）
    averageEfficiency.value = Math.floor(Math.random() * 20) + 80
    tokenTrend.value = (Math.random() - 0.5) * 30
    efficiencyTrend.value = (Math.random() - 0.5) * 10
    
    updateChartData()
  } finally {
    isLoading.value = false
  }
}

// 生命周期
onMounted(async () => {
  // 初始化时加载数据
  await refreshData()
  initChart()
  
  // 监听时间范围变化
  watch([selectedTimeframe, selectedModel], () => {
    refreshData()
  })
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script> 