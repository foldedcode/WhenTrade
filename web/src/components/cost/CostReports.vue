<template>
  <div class="card--od--refined p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-semibold" style="color: var(--od-text-primary)">{{ $t('cost.reports.title') }}</h2>
      <div class="flex items-center space-x-3">
        <!-- 时间范围选择 -->
        <select
          v-model="selectedRange"
          class="input--od input--od--sm"
          @change="generateReport"
        >
          <option value="week">{{ $t('cost.reports.lastWeek') }}</option>
          <option value="month">{{ $t('cost.reports.lastMonth') }}</option>
          <option value="quarter">{{ $t('cost.reports.lastQuarter') }}</option>
          <option value="custom">{{ $t('cost.reports.custom') }}</option>
        </select>
        
        <!-- 导出按钮 -->
        <button
          @click="exportReport"
          class="btn--od btn--od--primary btn--od--sm flex items-center"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {{ $t('cost.reports.export') }}
        </button>
      </div>
    </div>
    
    <!-- 报表摘要 -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <p class="text-sm mb-1" style="color: var(--od-text-muted)">{{ $t('cost.reports.totalCost') }}</p>
        <p class="text-2xl font-bold" style="color: var(--od-text-primary)">${{ reportData.totalCost.toFixed(2) }}</p>
        <p class="text-xs mt-1" :style="{ color: reportData.costTrend >= 0 ? 'var(--od-color-error)' : 'var(--od-color-success)' }">
          {{ reportData.costTrend >= 0 ? '↑' : '↓' }} {{ Math.abs(reportData.costTrend) }}%
        </p>
      </div>
      
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <p class="text-sm mb-1" style="color: var(--od-text-muted)">{{ $t('cost.reports.totalTokens') }}</p>
        <p class="text-2xl font-bold" style="color: var(--od-text-primary)">{{ formatNumber(reportData.totalTokens) }}</p>
        <p class="text-xs mt-1" style="color: var(--od-text-secondary)">{{ $t('cost.reports.avgPerDay') }}: {{ formatNumber(reportData.avgTokensPerDay) }}</p>
      </div>
      
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <p class="text-sm mb-1" style="color: var(--od-text-muted)">{{ $t('cost.reports.mostUsedModel') }}</p>
        <p class="text-lg font-bold" style="color: var(--od-text-primary)">{{ reportData.mostUsedModel }}</p>
        <p class="text-xs mt-1" style="color: var(--od-text-secondary)">{{ reportData.mostUsedModelPercentage }}% {{ $t('cost.reports.ofUsage') }}</p>
      </div>
      
      <div class="card--od p-4" style="background: var(--od-bg-secondary)">
        <p class="text-sm mb-1" style="color: var(--od-text-muted)">{{ $t('cost.reports.efficiency') }}</p>
        <p class="text-2xl font-bold" style="color: var(--od-text-primary)">{{ reportData.efficiency }}%</p>
        <p class="text-xs mt-1" style="color: var(--od-text-secondary)">{{ $t('cost.reports.budgetUtilization') }}</p>
      </div>
    </div>
    
    <!-- 详细报表 -->
    <div class="space-y-6">
      <!-- 成本趋势图 -->
      <div>
        <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.reports.costTrend') }}</h3>
        <div class="h-64 rounded-lg p-4" style="background: var(--od-bg-primary)">
          <canvas ref="trendChart"></canvas>
        </div>
      </div>
      
      <!-- 模型使用分布 -->
      <div>
        <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.reports.modelDistribution') }}</h3>
        <div class="h-64 rounded-lg p-4" style="background: var(--od-bg-primary)">
          <canvas ref="distributionChart"></canvas>
        </div>
      </div>
      
      <!-- 详细数据表 -->
      <div>
        <h3 class="text-lg font-medium mb-4" style="color: var(--od-text-primary)">{{ $t('cost.reports.detailedData') }}</h3>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b" style="border-color: var(--od-border)">
                <th class="text-left py-2 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.reports.date') }}</th>
                <th class="text-right py-2 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.reports.cost') }}</th>
                <th class="text-right py-2 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.reports.tokens') }}</th>
                <th class="text-right py-2 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.reports.requests') }}</th>
                <th class="text-center py-2 px-4 text-sm font-medium" style="color: var(--od-text-secondary)">{{ $t('cost.reports.primaryModel') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in reportData.dailyData"
                :key="row.date"
                class="border-b" style="border-color: var(--od-border)"
              >
                <td class="py-2 px-4" style="color: var(--od-text-secondary)">{{ formatDate(row.date) }}</td>
                <td class="text-right py-2 px-4" style="color: var(--od-text-primary)">${{ row.cost.toFixed(2) }}</td>
                <td class="text-right py-2 px-4" style="color: var(--od-text-secondary)">{{ formatNumber(row.tokens) }}</td>
                <td class="text-right py-2 px-4" style="color: var(--od-text-secondary)">{{ row.requests }}</td>
                <td class="text-center py-2 px-4" style="color: var(--od-text-secondary)">{{ row.primaryModel }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCostStore } from '@/stores/cost'
import Chart from 'chart.js/auto'

const { t } = useI18n()
const costStore = useCostStore()

// 响应式数据
const selectedRange = ref('week')
const trendChart = ref<HTMLCanvasElement>()
const distributionChart = ref<HTMLCanvasElement>()
let trendChartInstance: Chart | null = null
let distributionChartInstance: Chart | null = null

// 报表数据
const reportData = ref({
  totalCost: 0,
  costTrend: 0,
  totalTokens: 0,
  avgTokensPerDay: 0,
  mostUsedModel: 'GPT-3.5-Turbo',
  mostUsedModelPercentage: 65,
  efficiency: 87,
  dailyData: [] as Array<{
    date: string
    cost: number
    tokens: number
    requests: number
    primaryModel: string
  }>
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

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric'
  })
}

const generateReport = async () => {
  // 根据选择的时间范围生成报表
  const days = selectedRange.value === 'week' ? 7 :
               selectedRange.value === 'month' ? 30 :
               selectedRange.value === 'quarter' ? 90 : 30
  
  // 获取数据
  await costStore.fetchUsageSummary(days)
  await costStore.fetchUsageDetails({ limit: days })
  
  // 计算报表数据
  const summary = costStore.usageSummary
  const details = costStore.usageDetails
  
  if (summary) {
    reportData.value.totalCost = summary.total_cost
    reportData.value.totalTokens = summary.total_tokens
    reportData.value.avgTokensPerDay = summary.total_tokens / days
    
    // 找出使用最多的模型
    const modelBreakdown = summary.model_breakdown
    let maxUsage = 0
    let topModel = ''
    for (const [model, data] of Object.entries(modelBreakdown)) {
      if (data.percentage > maxUsage) {
        maxUsage = data.percentage
        topModel = model
      }
    }
    reportData.value.mostUsedModel = topModel
    reportData.value.mostUsedModelPercentage = Math.round(maxUsage)
  }
  
  // 生成每日数据
  const dailyMap = new Map<string, any>()
  details.forEach(detail => {
    const date = new Date(detail.date).toISOString().split('T')[0]
    if (!dailyMap.has(date)) {
      dailyMap.set(date, {
        date,
        cost: 0,
        tokens: 0,
        requests: 0,
        models: new Map()
      })
    }
    
    const day = dailyMap.get(date)
    day.cost += detail.cost
    day.tokens += detail.total_tokens
    day.requests += 1
    
    const modelCount = day.models.get(detail.model) || 0
    day.models.set(detail.model, modelCount + 1)
  })
  
  reportData.value.dailyData = Array.from(dailyMap.values()).map(day => {
    // 找出当天使用最多的模型
    let primaryModel = ''
    let maxCount = 0
    for (const [model, count] of day.models) {
      if (count > maxCount) {
        maxCount = count
        primaryModel = model
      }
    }
    
    return {
      date: day.date,
      cost: day.cost,
      tokens: day.tokens,
      requests: day.requests,
      primaryModel
    }
  }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  
  // 计算成本趋势
  if (reportData.value.dailyData.length >= 2) {
    const recentCost = reportData.value.dailyData.slice(-7).reduce((sum, d) => sum + d.cost, 0)
    const previousCost = reportData.value.dailyData.slice(-14, -7).reduce((sum, d) => sum + d.cost, 0)
    reportData.value.costTrend = previousCost > 0 ? ((recentCost - previousCost) / previousCost * 100) : 0
  }
  
  updateCharts()
}

const initCharts = () => {
  // 初始化趋势图
  if (trendChart.value) {
    const ctx = trendChart.value.getContext('2d')
    if (ctx) {
      trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: t('cost.reports.dailyCost'),
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
            }
          },
          scales: {
            x: {
              grid: {
                color: '#374151'
              },
              ticks: {
                color: '#9CA3AF'
              }
            },
            y: {
              grid: {
                color: '#374151'
              },
              ticks: {
                color: '#9CA3AF',
                callback: (value) => `$${value}`
              }
            }
          }
        }
      })
    }
  }
  
  // 初始化分布图
  if (distributionChart.value) {
    const ctx = distributionChart.value.getContext('2d')
    if (ctx) {
      distributionChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: [],
          datasets: [{
            data: [],
            backgroundColor: [
              '#3B82F6',
              '#10B981',
              '#8B5CF6',
              '#F59E0B',
              '#EF4444'
            ]
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: {
                color: '#F3F4F6'
              }
            }
          }
        }
      })
    }
  }
}

const updateCharts = () => {
  // 更新趋势图
  if (trendChartInstance) {
    trendChartInstance.data.labels = reportData.value.dailyData.map(d => formatDate(d.date))
    trendChartInstance.data.datasets[0].data = reportData.value.dailyData.map(d => d.cost)
    trendChartInstance.update()
  }
  
  // 更新分布图
  if (distributionChartInstance && costStore.usageSummary) {
    const breakdown = costStore.usageSummary.model_breakdown
    const models = Object.entries(breakdown).sort((a, b) => b[1].cost - a[1].cost).slice(0, 5)
    
    distributionChartInstance.data.labels = models.map(([name]) => name)
    distributionChartInstance.data.datasets[0].data = models.map(([, data]) => data.cost)
    distributionChartInstance.update()
  }
}

const exportReport = () => {
  // 生成CSV数据
  const headers = ['Date', 'Cost ($)', 'Tokens', 'Requests', 'Primary Model']
  const rows = reportData.value.dailyData.map(row => [
    row.date,
    row.cost.toFixed(2),
    row.tokens.toString(),
    row.requests.toString(),
    row.primaryModel
  ])
  
  const csv = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')
  
  // 下载CSV文件
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `cost-report-${selectedRange.value}-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// 生命周期
onMounted(() => {
  initCharts()
  generateReport()
})

onUnmounted(() => {
  if (trendChartInstance) {
    trendChartInstance.destroy()
  }
  if (distributionChartInstance) {
    distributionChartInstance.destroy()
  }
})

// 监听范围变化
watch(selectedRange, () => {
  generateReport()
})
</script>