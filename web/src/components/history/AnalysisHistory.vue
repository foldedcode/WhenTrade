<template>
  <div class="h-full flex flex-col" style="overflow: visible;">

    <!-- 筛选和控制面板 - 融合风格 -->
    <div class="filter-panel">
      <div class="flex items-center space-x-4">
        <div class="form-group">
          <label class="form-label">{{ t('history.filters.timeRange') }}</label>
          <ProfessionalDropdown
            v-model="filterTimeRange"
            :options="timeRangeOptions"
            :placeholder="t('history.filters.allTime')"
            size="sm"
            class="w-full"
          />
        </div>
        
        <div class="form-group flex-1 max-w-xs">
          <label class="form-label">{{ t('history.filters.search') }}</label>
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="t('history.filters.searchPlaceholder')"
              class="search-input"
            />
            <span class="absolute right-3 top-1/2 transform -translate-y-1/2 opacity-70">🔍</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="flex-1 scrollbar--professional py-4 px-4" style="overflow-y: auto;">
      <div class="space-y-3">
        <div
          v-for="analysis in filteredAnalyses"
          :key="analysis.id"
          class="history-item"
          @click="viewAnalysis(analysis)"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center space-x-3 mb-2">
                <span class="badge badge--primary">{{ (analysis.config?.symbol || 'N/A').toUpperCase() }}</span>
                <span class="badge badge--success">{{ t('analysis.depth') }} {{ analysis.config?.depth || 1 }}</span>
                <span class="badge badge--info">{{ getLanguageDisplay(analysis.config?.language) }}</span>
              </div>
              
              <div class="history-item-date">
                {{ formatDate(analysis.timestamp) }}
              </div>
              
              <div class="mt-2">
                <div class="flex items-center space-x-6">
                  <span class="flex items-center space-x-2">
                    <span class="history-item-label">{{ t('history.detail.cost').toUpperCase() }}:</span>
                    <span class="history-item-value">{{ formatCostWithCurrency(analysis) }}</span>
                  </span>
                  <span class="flex items-center space-x-2">
                    <span class="history-item-label">{{ t('history.detail.model').toUpperCase() }}:</span>
                    <span class="history-item-value">{{ getModelDisplay(analysis) }}</span>
                  </span>
                  <span class="flex items-center space-x-2">
                    <span class="history-item-label">{{ t('history.detail.duration').toUpperCase() }}:</span>
                    <span class="history-item-value">{{ Math.round(analysis.duration / 1000) }}s</span>
                  </span>
                </div>
              </div>
            </div>
            
            <div class="flex items-center space-x-2">
              <button
                @click.stop="handleShare(analysis)"
                class="action-btn action-btn--primary"
                :title="t('history.actions.share')"
              >
                🔗
              </button>
              <button
                @click.stop="handleExport(analysis)"
                class="action-btn action-btn--success"
                :title="t('history.actions.export')"
              >
                📥
              </button>
              <button
                @click.stop="deleteAnalysis(analysis.id)"
                class="action-btn action-btn--danger"
                :title="t('history.actions.delete')"
              >
                🗑️
              </button>
            </div>
          </div>
          
        </div>
      </div>
      
      <!-- 空状态 -->
      <EmptyState
        v-if="filteredAnalyses.length === 0"
        icon="📊"
        :title="t('history.empty.title')"
        :description="t('history.empty.description')"
      />
    </div>
    

    <!-- 详情模态框 -->
    <AnalysisDetailModal
      :visible="showDetailModal"
      :analysis="selectedAnalysis"
      @close="closeDetailModal"
      @export="handleExport"
      @share="handleShare"
    />
    
    <!-- 删除确认对话框 -->
    <ConfirmDialog
      :visible="showDeleteConfirm"
      :title="t('history.delete')"
      :message="t('history.deleteConfirm')"
      :description="t('common.irreversible')"
      icon="🗑️"
      type="danger"
      :confirm-text="t('common.delete')"
      :cancel-text="t('common.cancel')"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAnalysisStore } from '../../stores/analysis'
import AnalysisDetailModal from './AnalysisDetailModal.vue'
import ProfessionalDropdown from '../ui/ProfessionalDropdown.vue'
import ConfirmDialog from '../ui/ConfirmDialog.vue'
import EmptyState from '../ui/EmptyState.vue'
import { useSimpleToast } from '../../composables/useSimpleToast'

const { showSuccess } = useSimpleToast()
const { t } = useI18n()

const analysisStore = useAnalysisStore()

// 模态框状态
const showDetailModal = ref(false)
const selectedAnalysis = ref(null)

// 筛选器
const filterTimeRange = ref('all')
const searchQuery = ref('')

// 下拉框选项
const timeRangeOptions = computed(() => [
  { value: 'all', label: t('history.filters.allTime') },
  { value: 'today', label: t('common.time.today') },
  { value: 'week', label: t('common.time.thisWeek') },
  { value: 'month', label: t('common.time.thisMonth') }
])

// 计算属性
const totalAnalyses = computed(() => analysisStore.analysisHistory.length)
const totalCost = computed(() => 
  analysisStore.analysisHistory.reduce((sum, item) => sum + (item.cost || 0), 0)
)
const avgDuration = computed(() => {
  if (analysisStore.analysisHistory.length === 0) return 0
  const total = analysisStore.analysisHistory.reduce((sum, item) => sum + item.duration, 0)
  return Math.round(total / analysisStore.analysisHistory.length / 1000)
})
const successRate = computed(() => 100) // 简化处理，假设全部成功

const filteredAnalyses = computed(() => {
  let filtered = analysisStore.analysisHistory
  
  // 时间范围筛选
  if (filterTimeRange.value !== 'all') {
    const now = Date.now()
    const ranges = {
      today: 24 * 60 * 60 * 1000,
      week: 7 * 24 * 60 * 60 * 1000,
      month: 30 * 24 * 60 * 60 * 1000
    }
    const cutoff = now - ranges[filterTimeRange.value as keyof typeof ranges]
    filtered = filtered.filter(item => item.timestamp > cutoff)
  }
  
  // 搜索筛选
  if (searchQuery.value) {
    filtered = filtered.filter(item => 
      (item.config as any)?.symbol?.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }
  
  return filtered.sort((a, b) => b.timestamp - a.timestamp)
})

// 方法
const getMarketType = (type: string) => {
  // 检查是否存在特定的市场类型翻译
  const validTypes = ['crypto']
  const typeKey = validTypes.includes(type) ? type : 'unknown'
  const key = `common.marketTypes.${typeKey}`
  return t(key)
}

const formatDate = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleString()
}

// 根据provider格式化成本显示
const formatCostWithCurrency = (analysis: any) => {
  const cost = analysis.cost || 0
  const provider = analysis.config?.llmProvider || analysis.config?.llm_provider || ''
  
  // 检查是否是中国提供商（使用人民币）
  const normalizedProvider = provider.toLowerCase()
  const isCNYProvider = ['deepseek', 'kimi', 'moonshot'].includes(normalizedProvider)
  
  const currency = isCNYProvider ? '¥' : '$'
  return `${currency}${cost.toFixed(3)}`
}

// 获取模型显示格式
const getModelDisplay = (analysis: any) => {
  const provider = analysis.config?.llmProvider || analysis.config?.llm_provider || ''
  const model = analysis.config?.llmModel || analysis.config?.llm_model || ''
  
  // 智能格式化provider名称
  const formatProviderName = (provider: string) => {
    const providerMap: Record<string, string> = {
      'openai': 'OpenAI',
      'deepseek': 'DeepSeek', 
      'moonshot': 'Moonshot',
      'kimi': 'Kimi',
      'claude': 'Claude',
      'gemini': 'Gemini'
    }
    return providerMap[provider.toLowerCase()] || provider.charAt(0).toUpperCase() + provider.slice(1).toLowerCase()
  }
  
  const providerName = formatProviderName(provider)
  
  // 简化模型名称显示（去除provider前缀）
  const simplifyModel = (model: string, provider: string) => {
    const lowerModel = model.toLowerCase()
    const lowerProvider = provider.toLowerCase()
    
    // 如果模型名包含provider名称，去除前缀
    if (lowerModel.startsWith(lowerProvider)) {
      return model.substring(provider.length).replace(/^[-_]/, '')
    }
    return model
  }
  
  if (!model) return providerName || 'N/A'
  
  const simplifiedModel = simplifyModel(model, provider)
  return `${providerName}/${simplifiedModel}`
}

// 获取语言显示格式
const getLanguageDisplay = (language: string | undefined) => {
  if (!language) {
    // 对于没有语言信息的旧记录，根据当前系统语言推断可能的使用语言
    const currentLocale = localStorage.getItem('when-trade-locale') || 'zh-CN'
    return currentLocale.startsWith('zh') ? '中文' : 'EN'
  }
  
  const languageMap: Record<string, string> = {
    'zh-CN': '中文',
    'zh': '中文', 
    'en-US': 'EN',
    'en': 'EN'
  }
  
  return languageMap[language.toLowerCase()] || language.toUpperCase()
}


const viewAnalysis = (analysis: any) => {
  selectedAnalysis.value = analysis
  showDetailModal.value = true
}

const closeDetailModal = () => {
  showDetailModal.value = false
  selectedAnalysis.value = null
}

const handleExport = (analysis: any) => {
  // 导出为JSON文件
  const dataStr = JSON.stringify(analysis, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `analysis-${analysis.config?.symbol || 'unknown'}-${analysis.id}.json`
  link.click()
  URL.revokeObjectURL(url)
}

const handleShare = (analysis: any) => {
  // 创建分享数据
  const shareData = {
    title: `When.Trade - ${analysis.config?.symbol || 'Unknown'} 分析报告`,
    text: `${analysis.config?.symbol || 'Unknown'} 的${getMarketType(analysis.config?.marketType || 'unknown')}分析报告`,
    url: `${window.location.origin}/share/${analysis.id}`
  }
  
  // 使用Web Share API
  if (navigator.share) {
    navigator.share(shareData).catch(() => {/* Share failed - handled silently */})
  } else {
    // 回退到复制链接
    const shareUrl = `${window.location.origin}/share/${analysis.id}`
    navigator.clipboard.writeText(shareUrl).then(() => {
      showSuccess('分享链接已复制到剪贴板！')
    })
  }
}

// 删除确认状态
const showDeleteConfirm = ref(false)
const deletingAnalysisId = ref<string | null>(null)

const deleteAnalysis = (id: string) => {
  deletingAnalysisId.value = id
  showDeleteConfirm.value = true
}

const confirmDelete = () => {
  if (deletingAnalysisId.value) {
    const index = analysisStore.analysisHistory.findIndex(item => item.id === deletingAnalysisId.value)
    if (index > -1) {
      analysisStore.analysisHistory.splice(index, 1)
    }
  }
  showDeleteConfirm.value = false
  deletingAnalysisId.value = null
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
  deletingAnalysisId.value = null
}

</script>

<style scoped>
/* 统计卡片 */
.stat-card {
  @apply p-4 rounded-lg transition-all;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
}

.stat-card:hover {
  border-color: var(--od-primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-od-md);
}

.stat-card--warning:hover {
  border-color: var(--od-warning);
}

.stat-card--success:hover {
  border-color: var(--od-success);
}

.stat-label {
  @apply text-xs font-bold tracking-wider uppercase mb-1;
  color: var(--od-text-muted);
}

.stat-value {
  @apply text-2xl font-bold;
  color: var(--od-text-primary);
}

.stat-card--warning .stat-label {
  color: var(--od-warning);
}

.stat-card--warning .stat-value {
  color: var(--od-warning);
}

.stat-card--success .stat-label {
  color: var(--od-success);
}

.stat-card--success .stat-value {
  color: var(--od-success);
}

/* 筛选面板 */
.filter-panel {
  @apply p-4 rounded-lg mb-4 mx-4;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
}

.form-label {
  @apply text-xs font-bold tracking-wider uppercase mb-1 block;
  color: var(--od-text-muted);
}

.search-input {
  @apply w-full px-3 py-2 rounded-md focus:outline-none;
  background: var(--od-background);
  border: 1px solid var(--od-border);
  color: var(--od-text-primary);
}

.search-input:focus {
  border-color: var(--od-primary);
}

/* 历史记录项 */
.history-item {
  @apply p-4 rounded-lg transition-all cursor-pointer;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
  margin-bottom: 0.75rem;
}

.history-item:hover {
  border-left: 4px solid var(--od-primary);
  transform: translateX(2px);
  box-shadow: var(--shadow-od-md);
}

.history-item-date {
  @apply text-sm;
  color: var(--od-text-secondary);
}

.history-item-label {
  @apply text-xs font-bold tracking-wider;
  color: var(--od-text-muted);
}

.history-item-value {
  @apply text-sm font-medium;
  color: var(--od-text-primary);
}

.history-item-summary {
  @apply mt-3 p-3 rounded;
  background: var(--od-background);
  border: 1px solid var(--od-border);
  color: var(--od-text-secondary);
  font-size: 0.75rem;
}

/* 徽章 */
.badge {
  @apply px-2 py-1 text-xs font-bold tracking-wider rounded;
}

.badge--primary {
  background: var(--od-primary);
  color: var(--od-background);
}

.badge--warning {
  background: var(--od-warning);
  color: var(--od-background);
}

.badge--success {
  background: var(--od-success);
  color: var(--od-background);
}

.badge--info {
  background: var(--od-info, #3b82f6);
  color: var(--od-background);
}

/* 操作按钮 */
.action-btn {
  @apply w-8 h-8 flex items-center justify-center rounded transition-all;
  border: 1px solid;
}

.action-btn--primary {
  border-color: var(--od-primary);
  color: var(--od-primary);
}

.action-btn--primary:hover {
  background: var(--od-primary);
  color: var(--od-background);
}

.action-btn--success {
  border-color: var(--od-success);
  color: var(--od-success);
}

.action-btn--success:hover {
  background: var(--od-success);
  color: var(--od-background);
}

.action-btn--danger {
  border-color: var(--od-danger);
  color: var(--od-danger);
}

.action-btn--danger:hover {
  background: var(--od-danger);
  color: var(--od-background);
}

/* 滚动条 */
.scrollbar--professional {
  scrollbar-width: thin;
  scrollbar-color: var(--od-border) transparent;
}

.scrollbar--professional::-webkit-scrollbar {
  width: 6px;
}

.scrollbar--professional::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar--professional::-webkit-scrollbar-thumb {
  background: var(--od-border);
  border-radius: 3px;
}

.scrollbar--professional::-webkit-scrollbar-thumb:hover {
  background: var(--od-border-light);
}

</style>
