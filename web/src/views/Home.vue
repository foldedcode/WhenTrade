<template>
  <div class="h-full overflow-hidden" style="background: var(--od-background); color: var(--od-text-primary);">
    <!-- 主工作区域 - 全高度 -->
    <main class="h-full flex flex-col">
      <div class="flex-1 flex flex-col min-h-0">
            <!-- 精致标签页导航 - 修复悬浮溢出 -->
        <div class="mx-4 lg:mx-6 pt-4 pb-3 flex-shrink-0">
          <nav class="tabs--od--refined rounded-lg" style="overflow: visible;">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="switchTab(tab.id)"
              :disabled="analysisStore.isAnalyzing && tab.id !== activeTab"
              :class="[
                'tab--od--refined relative flex items-center justify-center',
                activeTab === tab.id && 'tab--od--refined--active',
                analysisStore.isAnalyzing && tab.id !== activeTab && 'tab--od--refined--disabled'
              ]"
            >
              <div class="flex items-center justify-center">
                <PixelIcon :name="tab.icon" class="mr-2" />
                <span class="font-medium relative z-10">{{ $t(tab.label) }}</span>
                <span v-if="tab.badge" :class="[
                  'badge--od--refined ml-2 px-2 py-0.5 relative z-10',
                  tab.id === 'history' ? 'badge--od--refined--terminal' : 'badge--od--refined--primary'
                ]">{{ tab.badge }}</span>
              </div>
            </button>
          </nav>
        </div>

        <!-- 页面内容区域 - 统一固定高度容器 -->
        <div class="mx-4 lg:mx-6 px-1 pt-1 pb-4 flex-1 min-h-0" style="overflow: hidden;">
          <!-- 分析页面 -->
          <div v-show="activeTab === 'analysis'" class="h-full flex flex-col lg:flex-row gap-3">
            <!-- 左侧配置面板 - 优化布局，合并分析师团队与状态 -->
            <div class="w-[20%] h-full flex flex-col hidden lg:flex">
              <div class="card--od--refined card--od--interactive flex-1 flex flex-col min-h-0">
                <div class="section__header--od section__header--od--dark">
                  <div class="section__title--od">{{ $t('common.analysis.configuration') }}</div>
                </div>
                
                <div class="flex-1 overflow-y-auto">
                  <!-- 配置内容 - 超紧凑布局 -->
                  <div class="section__content--od space-y-2">
                    <!-- 市场类型选择器 -->
                    <MarketTypeSelector 
                      v-model="form.marketType"
                      :disabled="analysisStore.isAnalyzing"
                      @change="handleMarketTypeChange"
                    />
                    
                    <!-- 分析标的 -->
                    <div class="form-group">
                      <label class="block text-xs font-medium mb-1" style="color: var(--od-text-secondary)">{{ $t('common.analysis.target') }}</label>
                      
                      <!-- 左右布局：预设与自定义 -->
                      <div class="grid grid-cols-2 gap-2">
                        <!-- 预设选择 -->
                        <div>
                          <ProfessionalDropdown
                            v-model="presetSymbol"
                            :options="filteredPresetSymbolOptions"
                            :placeholder="$t('common.analysis.selectPreset')"
                            :disabled="analysisStore.isAnalyzing"
                            size="sm"
                            @update:modelValue="handlePresetChange"
                          />
                        </div>
                        
                        <!-- 自定义输入 -->
                        <div>
                          <input 
                            v-model="customSymbol" 
                            type="text" 
                            :placeholder="$t('common.analysis.customTarget')"
                            :disabled="analysisStore.isAnalyzing"
                            class="input--od w-full text-sm"
                            @input="handleCustomInput"
                          />
                        </div>
                      </div>
                      
                      <!-- 提示文本 -->
                      <div class="text-xs mt-1" style="color: var(--od-text-muted)">
{{ $t('common.analysis.selectPresetHint') }}
                      </div>
                    </div>
                    
                    <!-- LLM配置 - 带介绍和智能默认值 -->
                    <div class="form-group">
                      <div class="grid grid-cols-2 gap-2">
                        <div>
                          <label class="block text-xs font-medium mb-1" style="color: var(--od-text-secondary)">{{ $t('common.analysis.llmProvider') }}</label>
                          <ProfessionalDropdown
                            v-model="form.llmProvider"
                            :options="llmProviderOptionsWithProvider"
                            :placeholder="$t('common.analysis.selectLLMProvider')"
                            :disabled="analysisStore.isAnalyzing"
                            show-logo
                            searchable
                            size="sm"
                            @update:modelValue="handleProviderChange"
                          />
                        </div>
                        
                        <div>
                          <label class="block text-xs font-medium mb-1" style="color: var(--od-text-secondary)">{{ $t('common.analysis.model') }}</label>
                          <ProfessionalDropdown
                            v-model="form.llmModel"
                            :options="modelOptions"
                            :placeholder="$t('common.analysis.selectModel')"
                            :disabled="analysisStore.isAnalyzing"
                            size="sm"
                          />
                        </div>
                      </div>
                      <!-- LLM介绍 - 单行注释样式 -->
                      <div class="text-xs mt-0.5 mb-0 whitespace-nowrap overflow-hidden text-ellipsis" style="color: var(--ft-text-muted)">
                        <span 
                          class="italic cursor-help" 
                          :title="getLLMDescription(form.llmProvider)"
                        >
                          {{ getLLMDescription(form.llmProvider) }}
                        </span>
                      </div>
                    </div>
                    
                    <!-- 分析深度配置 -->
                    <AnalysisDepthConfig
                      v-model="form.depth"
                      :market-type="form.marketType"
                      :disabled="analysisStore.isAnalyzing"
                      :key="`depth-config-${form.marketType}`"
                    />

                    <!-- 时间范围选择器（根据市场类型显示） -->
                    <TimeRangeSelector 
                      v-if="currentMarketConfig?.hasTimeFrame"
                      v-model="form.timeRange"
                      :disabled="analysisStore.isAnalyzing"
                    />
                    
                    <!-- 分析范围选择器 -->
                    <AnalysisScopeSelector
                      v-model="form.analysisScopes"
                      :market-type="form.marketType"
                      :max-selection="5"
                      :scope-configs="scopeConfigs"
                      :disabled="analysisStore.isAnalyzing"
                      @update:scopeConfigs="handleScopeConfigsUpdate"
                      @configure="openScopeConfig"
                    />
                    
                    <!-- 分析师团队与状态合并 - 优化悬停特效（隐藏） -->
                    <div v-if="false" class="form-group">
                      <label class="block text-xs font-medium mb-1" style="color: var(--ft-text-secondary)">{{ $t('common.analysis.analystTeam') }}</label>
                      <div class="space-y-1">
                        <div
                          v-for="analyst in availableAnalysts"
                          :key="analyst.id"
                          class="analyst-card--professional--compact hover--glow"
                          :class="{ 
                            'analyst-card--selected': form.analysts.includes(analyst.id),
                            'analyst-card--active': analysisStore.isAnalyzing && isAnalystActive(analyst.id)
                          }"
                          @click="toggleAnalyst(analyst.id)"
                        >
                          <div class="flex items-center space-x-3">
                            <!-- 现代化分析师徽章 -->
                            <div class="analyst-badge-modern" 
                                 :class="[
                                   `analyst-badge--${analyst.category}`,
                                   { 'analyst-badge--selected': form.analysts.includes(analyst.id) }
                                 ]">
                              <div class="analyst-badge__gradient-bg"></div>
                              <div class="analyst-badge__icon">
                                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                  <path :d="analyst.iconPath" />
                                </svg>
                              </div>
                              <!-- 分析进度环 -->
                              <div v-if="analysisStore.isAnalyzing && form.analysts.includes(analyst.id)" 
                                   class="analyst-progress-ring">
                                <svg class="w-full h-full" viewBox="0 0 36 36">
                                  <circle cx="18" cy="18" r="16" fill="none" stroke="var(--od-border)" stroke-width="2" opacity="0.2"/>
                                  <circle cx="18" cy="18" r="16" fill="none" stroke="var(--od-primary)" stroke-width="2"
                                          :stroke-dasharray="`${getAnalystProgress(analyst.id) * 100.53 / 100}, 100.53`"
                                          stroke-dashoffset="25.13"
                                          stroke-linecap="round"
                                          transform="rotate(-90 18 18)"/>
                                </svg>
                              </div>
                            </div>
                            
                            <div class="flex-1">
                              <div class="text-xs font-medium" style="color: var(--ft-text-primary)">{{ analyst.name }}</div>
                              <div class="text-xs" style="color: var(--ft-text-muted)">
                                <span v-if="analysisStore.isAnalyzing && isAnalystActive(analyst.id)" style="color: var(--od-primary)">
{{ $t('common.analysis.analyzing') }}
                                </span>
                                <span v-else>{{ analyst.description }}</span>
                              </div>
                            </div>
                            <div class="flex items-center space-x-1">
                              <div class="w-1.5 h-1.5 rounded-full transition-all duration-200" 
                                   :class="getAnalystStatus(analyst.id)"></div>
                              <span class="text-xs" style="color: var(--ft-text-muted)">{{ getAnalystProgress(analyst.id) }}%</span>
                            </div>
                          </div>
                          
                          <!-- 底部进度条 -->
                          <div v-if="analysisStore.isAnalyzing && form.analysts.includes(analyst.id)" 
                               class="analyst-progress-bar-container">
                            <div class="analyst-progress-bar-fill" 
                                 :style="{ width: `${getAnalystProgress(analyst.id)}%` }"></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                  </div>
                </div>
              </div>
            </div>

            <!-- 移动端配置面板 -->
            <div class="w-full h-auto lg:hidden mb-3">
              <div class="card--od--refined card--od--interactive p-4">
                <h3 class="text-sm font-medium mb-3">{{ $t('common.analysis.configuration') }}</h3>
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="text-xs text-gray-500">{{ $t('analysis.symbol') }}</label>
                    <div class="text-sm font-medium">{{ form.symbol || $t('common.notSelected') }}</div>
                  </div>
                  <div>
                    <label class="text-xs text-gray-500">{{ $t('analysis.depth') }}</label>
                    <div class="text-sm font-medium">{{ form.depth || $t('common.notSelected') }}</div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 中央主工作区 - 流程编辑器 -->
            <div class="flex-1 h-full min-w-0 w-full">
              <!-- 直接渲染实用控制台 -->
              <component
                :is="currentConsoleComponent"
                :form-data="form"
                :scope-configs="scopeConfigs"
                :is-analyzing="analysisStore.isAnalyzing"
                @start-analysis="handleAnalysisStart"
                @stop-analysis="handleAnalysisStop"
              />
                  
              <!-- 经典模式 - 原有的进度显示 -->
              <div v-if="false" class="card--od--refined card--od--interactive h-full flex flex-col">
                <div class="section__header--od section__header--od--dark">
                  <div class="section__title--od">{{ $t('common.analysis.progress') }}</div>
                  <div class="flex items-center space-x-3">
                    <span class="text-xs px-2 py-1 rounded" style="background: var(--od-background-light); color: var(--od-text-secondary);">
                      {{ currentStep }}/{{ totalSteps }}
                    </span>
                    <span class="text-sm font-semibold" style="color: var(--od-text-primary)">{{ formatProgress(analysisStore.analysisProgress) }}%</span>
                    <button
                      @click="switchToFlowMode"
                      class="btn--od btn--od--ghost btn--od--sm"
                    >
                      <PixelIcon name="share" class="mr-1" />
                      {{ $t('analysis.flowEditor.flowMode') }}
                    </button>
                  </div>
                </div>

                <!-- 专业进度条 -->
                <div class="px-4 py-3">
                  <div class="analysis-progress-container">
                    <div class="analysis-progress-track">
                      <div 
                        class="analysis-progress-fill"
                        :style="{ width: `${analysisStore.analysisProgress}%` }"
                      >
                        <div class="analysis-progress-glow"></div>
                      </div>
                    </div>
                  </div>
                  <div class="flex justify-between text-xs mt-2" style="color: var(--od-text-muted)">
                    <span>{{ getCurrentStepName() }}</span>
                    <span>{{ $t('common.analysis.percentComplete', { percent: Math.round(analysisStore.analysisProgress) }) }}</span>
                  </div>
                </div>

                <div class="flex-1 overflow-y-auto">
                  <div v-if="!analysisStore.currentResult" class="h-full flex items-center justify-center p-6">
                    <div v-if="!analysisStore.isAnalyzing" class="text-center">
                      <svg class="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="color: var(--od-text-muted);">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      <h3 class="text-lg font-medium mb-2" style="color: var(--od-text-secondary)">{{ $t('common.analysis.readyToStart') }}</h3>
                      <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('common.analysis.configureAndStart') }}</p>
                    </div>
                    
                    <div v-else class="text-center">
                      <div class="w-16 h-16 mx-auto mb-4">
                        <div class="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                      </div>
                      <h3 class="text-lg font-medium mb-2" style="color: var(--od-text-secondary)">{{ $t('common.analysis.inProgress') }}</h3>
                      <p class="text-sm" style="color: var(--od-text-muted)">{{ $t('common.analysis.analyzingSymbol', { symbol: form.symbol }) }}</p>
                    </div>
                  </div>
                  
                  <!-- 分析结果 - 固定高度容器，内部滚动优化 -->
                  <div v-else class="p-4 h-full flex flex-col">
                    <div class="flex items-center justify-between mb-3 flex-shrink-0">
                      <h3 class="text-lg font-semibold" style="color: var(--od-text-primary)">{{ $t('common.analysis.results') }}</h3>
                      <div class="flex items-center space-x-2">
                        <button 
                          @click="copyResult"
                          class="btn--od btn--od--ghost btn--od--sm"
                          :title="$t('common.analysis.copyResult')"
                        >
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                        <button 
                          @click="toggleResultExpanded"
                          class="btn--od btn--od--ghost btn--od--sm"
                          :title="resultExpanded ? $t('common.analysis.collapse') : $t('common.analysis.expand')"
                        >
                          <svg class="w-4 h-4 transition-transform duration-200" :class="{ 'rotate-180': resultExpanded }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    
                    <div class="flex-1" style="max-height: calc(100vh - 20rem);">
                      <div class="result-container--professional h-full overflow-y-auto">
                        <pre class="text-sm" style="color: var(--od-text-secondary); white-space: pre-wrap; word-break: break-word; font-family: 'Proto Mono', monospace;">{{ JSON.stringify(analysisStore.currentResult, null, 2) }}</pre>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 右侧信息面板 -->
            <div class="w-[20%] h-full flex flex-col hidden lg:flex">
              <div class="card--od--refined card--od--interactive flex-1 flex flex-col min-h-0">
                <div class="section__header--od section__header--od--dark">
                  <div>
                    <div class="section__title--od">{{ $t('common.cost.monitoring') }}</div>
                    <div class="section__subtitle--od">{{ $t('common.cost.realtimeTracking') }}</div>
                  </div>
                  <div></div>
                </div>
                
                <div class="flex-1 overflow-y-auto">
                  <!-- 成本监控区域 - 紧凑显示 -->
                  <div class="section__content--od">
                    <div class="space-y-2">
                      <div v-for="stat in costStore.providerStats" :key="stat.id" 
                           class="border-b pb-2" style="border-color: var(--od-border);">
                        <!-- 模型名称 -->
                        <div class="text-sm font-medium mb-1" style="color: var(--od-text-primary)">
                          {{ stat.label }}
                        </div>
                        <!-- Token数量和成本 -->
                        <div class="flex justify-between text-xs">
                          <span style="color: var(--od-text-muted)">
                            {{ stat.formattedTokens }} tokens
                          </span>
                          <span style="color: var(--od-color-success)">
                            {{ stat.formattedCost }}
                          </span>
                        </div>
                      </div>
                      
                      <!-- 无配置提供商时显示 -->
                      <div v-if="costStore.providerStats.length === 0" 
                           class="text-center py-4 text-sm" 
                           style="color: var(--od-text-muted)">
                        <div class="text-xl mb-1">⚙️</div>
                        <div>暂未配置LLM提供商</div>
                        <div class="text-xs mt-1">请先配置API密钥</div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 最近分析区域 -->
                  <div class="p-4 mt-2 border-t" style="border-color: var(--od-border);">
                    <h3 class="text-sm font-semibold mb-3" style="color: var(--od-text-primary)">{{ $t('common.recentAnalysis') }}</h3>
                    <div class="space-y-2">
                      <div
                        v-for="history in analysisStore.analysisHistory.slice(0, 5)"
                        :key="history.id"
                        class="card--od--refined p-3 cursor-pointer transition-all duration-200 hover:scale-[1.02]"
                        @click="viewHistoryDetail(history)"
                      >
                        <div class="flex justify-between items-start mb-1">
                          <span class="text-xs font-medium" style="color: var(--od-text-primary)">{{ history.config.symbol }}</span>
                          <span class="text-xs" style="color: var(--od-text-muted);">{{ formatTimestamp(history.timestamp) }}</span>
                        </div>
                        <div class="text-xs" style="color: var(--od-text-muted);">
                          {{ t('cost.recent.depth') }} {{ history.config?.depth || 1 }}
                        </div>
                        <div class="flex justify-between items-center mt-2">
                          <span class="text-xs text-green-400">${{ formatCost(history.cost) }}</span>
                          <span class="text-xs" style="color: var(--od-text-muted);">{{ Math.round(history.duration / 1000) }}s</span>
                        </div>
                      </div>
                      
                      <!-- 无历史记录时显示 -->
                      <div v-if="analysisStore.analysisHistory.length === 0" 
                           class="text-center py-4 text-xs"
                           style="color: var(--od-text-muted)">
                        {{ $t('table.noData') }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 其他标签页 - 统一高度容器 -->
          <div v-show="activeTab !== 'analysis'" class="h-full" style="overflow: visible;">
            <div class="h-full p-2" style="overflow: visible;">
              <div class="h-full">
                <!-- 分析历史页面 -->
                <div v-show="activeTab === 'history'" class="h-full">
                  <AnalysisHistory />
                </div>
                
                
                
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
    
    <!-- 分析详情模态框 -->
    <AnalysisDetailModal
      :visible="showAnalysisDetailModal"
      :analysis="selectedAnalysisForDetail"
      @close="closeAnalysisDetailModal"
      @export="handleAnalysisDetailExport"
    />
    
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import { useCostStore } from '../stores/cost'
import AnalysisHistory from '../components/history/AnalysisHistory.vue'
import AnalysisDetailModal from '../components/history/AnalysisDetailModal.vue'
import TimeRangeSelector from '../components/common/TimeRangeSelector.vue'
import ProfessionalDropdown from '../components/ui/ProfessionalDropdown.vue'
import PixelIcon from '@/components/ui/PixelIcon.vue'
import MarketTypeSelector from '@/components/analysis/MarketTypeSelector.vue'
import AnalysisScopeSelector from '@/components/analysis/AnalysisScopeSelector.vue'
import AnalysisDepthConfig from '@/components/analysis/AnalysisDepthConfig.vue'
import AgentConsolePractical from '@/components/analysis/AgentConsolePractical.vue'
import type { SelectOption } from '@/types'
import type { MarketType, MarketConfig } from '@/types/market'
import { marketConfigService } from '@/services/market-config.service'
import { analysisConfigService } from '@/services/analysis-config.service'
import { llmDetectionService, type LLMProvider, type LLMModel } from '@/services/llm-detection.service'
import { generateMarkdownReport, generateReportFromHistory } from '@/utils/reportGenerator'
import { consoleMessageService } from '@/services/console-message.service'

// 定义TimeRange类型
interface TimeRange {
  start: Date
  end: Date
  label: string
}

// 使用 i18n
const { locale, t } = useI18n()

// 使用路由
const route = useRoute()

// 使用 stores
const analysisStore = useAnalysisStore()
const costStore = useCostStore()

// 监听分析状态变化以进行调试
watch(() => analysisStore.isAnalyzing, (newValue, oldValue) => {
  // console.log(`🔍 [分析状态] ${oldValue} → ${newValue}`)
}, { immediate: true })

// 界面状态
const activeTab = ref('analysis')
const resultExpanded = ref(false)

// 分析详情模态框状态
const showAnalysisDetailModal = ref(false)
const selectedAnalysisForDetail = ref(null)

// 直接使用AgentConsolePractical组件
const currentConsoleComponent = AgentConsolePractical

// 终端模式配置
// 移除了视图模式选择，只保留电路板

// 分析步骤
const totalSteps = ref(7)
const currentStep = computed(() => Math.ceil((analysisStore.analysisProgress / 100) * totalSteps.value))

// LLM提供商和模型数据
const availableLLMProviders = ref<LLMProvider[]>([])
const currentProviderModels = ref<LLMModel[]>([])

// 表单数据
const form = ref({
  marketType: 'crypto' as MarketType, // 默认加密货币
  symbol: '',
  timeframe: '1h',
  timeRange: null as TimeRange | null,
  depth: null as number | null,
  analysisScopes: [] as string[], // 使用新的分析范围
  analysts: [] as string[], // 保留向后兼容
  llmProvider: '' as string | null,
  llmModel: '' as string | null
})

// 分析范围配置状态 - 从 localStorage 初始化
const storedScopeConfigs = localStorage.getItem('scope_configs')
const scopeConfigs = ref<Record<string, any>>(
  storedScopeConfigs ? JSON.parse(storedScopeConfigs) : {}
)

// 监听 scopeConfigs 变化并持久化到 localStorage
watch(scopeConfigs, (newConfigs) => {
  localStorage.setItem('scope_configs', JSON.stringify(newConfigs))
}, { deep: true })

// 工具配置对话框状态
const showToolConfig = ref(false)
const configScopeId = ref('')
const configScopeName = ref('')
const currentScopeConfig = ref<{ tools?: string[], dataSources?: string[] }>({})

// 当前市场配置
const currentMarketConfig = ref<MarketConfig | null>(null)

// 选项数据 - 移除旧的市场类型选项，由MarketTypeSelector组件处理

// 分析标的相关数据
const presetSymbol = ref('')
const customSymbol = ref('')
const presetSymbols = [
  // 加密货币热门
  { value: 'BTC/USDT', label: 'Bitcoin', category: 'crypto' },
  { value: 'ETH/USDT', label: 'Ethereum', category: 'crypto' },
  { value: 'BNB/USDT', label: 'Binance Coin', category: 'crypto' },
  { value: 'SOL/USDT', label: 'Solana', category: 'crypto' },
  { value: 'ADA/USDT', label: 'Cardano', category: 'crypto' },
  { value: 'DOGE/USDT', label: 'Dogecoin', category: 'crypto' },
  { value: 'MATIC/USDT', label: 'Polygon', category: 'crypto' },
  { value: 'AVAX/USDT', label: 'Avalanche', category: 'crypto' },
  
]

// 根据市场类型过滤预设标的选项
const filteredPresetSymbolOptions = computed(() => {
  const filtered = presetSymbols.filter(symbol => symbol.category === form.value.marketType)
  return [
    { value: '', label: t('common.analysis.selectPreset') },
    ...filtered
  ]
})

// 处理预设选择
const handlePresetChange = (value: string) => {
  if (value) {
    form.value.symbol = value
    customSymbol.value = '' // 清空自定义输入
  } else {
    // 选择空选项时，清空标的
    form.value.symbol = ''
    customSymbol.value = ''
  }
}

// 处理自定义输入
const handleCustomInput = () => {
  if (customSymbol.value) {
    form.value.symbol = customSymbol.value
    presetSymbol.value = '' // 清空预设选择
  }
}

// 监听 analysisScopes 变化，同步更新 analysts（向后兼容）
watch(() => form.value.analysisScopes, (newScopes) => {
  form.value.analysts = [...newScopes]
})

// 初始化时加载默认市场配置
onMounted(async () => {
  try {
    // 获取默认市场类型
    const defaultMarket = await marketConfigService.getDefaultMarket()
    const defaultConfig = await marketConfigService.getMarketConfig(defaultMarket)
    
    if (defaultConfig) {
      form.value.marketType = defaultMarket
      currentMarketConfig.value = defaultConfig
      
      // 初始化默认时间范围（但不设置默认深度）
      if (defaultConfig.defaultTimeFrame) {
        form.value.timeframe = defaultConfig.defaultTimeFrame
      }
    }
    
    // 确保 scopeConfigs 已经从 localStorage 加载
    // 由于已经在初始化时加载，这里只需要确认
    // console.log('Loaded scopeConfigs from localStorage:', scopeConfigs.value)
  } catch (error) {
    console.error('Failed to load default market config:', error)
  }
})

// 未使用的 LLM 提供商选项
// const llmProviderOptions: SelectOption[] = [
//   { value: 'openai', label: 'OpenAI' },
//   { value: 'anthropic', label: 'Anthropic' },
//   { value: 'google', label: 'Google' },
//   { value: 'local', label: t('common.aiProviders.local.name') }
// ]

const llmProviderOptionsWithProvider = computed(() => {
  const options = [
    { value: '', label: t('common.analysis.selectLLMProvider'), provider: '', description: '' }
  ]
  
  // 添加动态加载的提供商
  availableLLMProviders.value.forEach(provider => {
    if (provider.available) {
      options.push({
        value: provider.id,
        label: provider.name,
        provider: provider.id,
        description: t(`providers.${provider.id}.description`, provider.description)
      })
    }
  })
  
  return options
})


// 模型选项 - 基于选中的提供商动态生成
const modelOptions = computed(() => {
  if (!form.value.llmProvider || form.value.llmProvider === '') {
    return []
  }
  
  return currentProviderModels.value.map(model => ({
    value: model.id,
    label: model.name
  }))
})

// 时间范围
const timeRange = ref({
  start: new Date(Date.now() - 24 * 60 * 60 * 1000),
  end: new Date(),
  label: t('common.timeRange.past24h')
})

// 可用分析师 - 带专业图标
const availableAnalysts = computed(() => [
  { 
    id: 'technical_analyst', 
    name: t('common.analysts.technical.name'), 
    description: t('common.analysts.technical.description'),
    category: 'technical',
    iconPath: 'M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z'
  },
  { 
    id: 'fundamental_analyst', 
    name: t('common.analysts.fundamental.name'), 
    description: t('common.analysts.fundamental.description'),
    category: 'fundamental',
    iconPath: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  },
  { 
    id: 'sentiment_analyst', 
    name: t('common.analysts.sentiment.name'), 
    description: t('common.analysts.sentiment.description'),
    category: 'sentiment',
    iconPath: 'M7 8h10m0 0V6a2 2 0 00-2-2H9a2 2 0 00-2 2v2m10 0v10a2 2 0 01-2 2H9a2 2 0 01-2-2V8m10 0V6a2 2 0 00-2-2H9a2 2 0 00-2 2v2'
  },
  { 
    id: 'risk_analyst', 
    name: t('common.analysts.risk.name'), 
    description: t('common.analysts.risk.description'),
    category: 'risk',
    iconPath: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z'
  },
  { 
    id: 'market_analyst', 
    name: t('common.analysts.market.name'), 
    description: t('common.analysts.market.description'),
    category: 'market',
    iconPath: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064'
  }
])

// 标签页配置 - 重新排序为：分析配置 → 研究管理 → 分析历史 → 成本控制
const tabs = computed(() => [
  {
    id: 'analysis',
    label: 'common.tabs.analysis',
    icon: 'chart-bar',
    badge: analysisStore.isAnalyzing ? t('common.analysisStatus.running') : null
  },
  {
    id: 'history',
    label: 'common.tabs.history',
    icon: 'clock',
    badge: analysisStore.analysisHistory.length || null
  }
])

// 方法
const switchTab = (tab: string) => {
  // 分析运行期间禁止切换到其他标签
  if (analysisStore.isAnalyzing && tab !== activeTab.value) {
    console.warn('🚫 [防护] 分析运行期间禁止切换标签页，防止状态混乱')
    return
  }
  
  // console.log('🔄 [标签切换]', activeTab.value, '→', tab)
  activeTab.value = tab
}

const switchConsoleVersion = (versionId: string) => {
  currentConsoleVersion.value = versionId
  // console.log('切换到版本:', versionId)
}

const getVersionName = (versionId: string) => {
  const version = consoleVersions.value.find(v => v.id === versionId)
  return version?.name || '未知版本'
}

const toggleResultExpanded = () => {
  resultExpanded.value = !resultExpanded.value
}


const formatProgress = (progress: number): string => {
  return Math.round(progress).toString()
}

const formatCost = (cost: number | undefined): string => {
  return (cost || 0).toFixed(3)
}

const formatTimestamp = (timestamp: number): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return t('common.time.justNow')
  if (minutes < 60) return t('common.time.minutesAgo', { count: minutes })
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return t('common.time.hoursAgo', { count: hours })
  return date.toLocaleDateString(locale.value, {
    year: 'numeric',
    month: 'short', 
    day: 'numeric'
  })
}

const getMarketType = (type: string | undefined) => {
  if (!type) return t('common.marketTypes.unknown')
  const validTypes = ['stock', 'crypto', 'commodity']
  const typeKey = validTypes.includes(type) ? type : 'unknown'
  return t(`common.marketTypes.${typeKey}`)
}

const toggleAnalyst = (analystId: string) => {
  const index = form.value.analysts.indexOf(analystId)
  if (index > -1) {
    form.value.analysts.splice(index, 1)
  } else {
    form.value.analysts.push(analystId)
  }
}

// 处理市场类型变化
const handleMarketTypeChange = async (marketType: MarketType, config: MarketConfig) => {
  currentMarketConfig.value = config
  
  // 清空当前的分析范围选择
  form.value.analysisScopes = []
  
  // 同步更新分析师列表（向后兼容）
  form.value.analysts = form.value.analysisScopes
  
  // 清空分析标的
  presetSymbol.value = ''
  customSymbol.value = ''
  form.value.symbol = ''
  
  // 根据市场类型设置默认时间范围
  if (!config.hasTimeFrame) {
    form.value.timeframe = ''
  } else if (config.defaultTimeFrame) {
    form.value.timeframe = config.defaultTimeFrame
  }
  
  // 不设置默认深度，让用户自己选择
  // form.value.depth 保持为 null
}

const getAnalystStatus = (analystId: string) => {
  const agent = analysisStore.agents.find(a => a.id === analystId)
  if (!agent) return 'bg-gray-500'
  return {
    online: 'bg-green-500',
    busy: 'bg-yellow-500',
    offline: 'bg-red-500',
    idle: 'bg-gray-500',
    analyzing: 'bg-blue-500',
    completed: 'bg-green-500',
    debating: 'bg-purple-500',
    failed: 'bg-red-500',
    thinking: 'bg-indigo-500'
  }[agent.status] || 'bg-gray-500'
}

const getAnalystProgress = (analystId: string) => {
  // 模拟每个分析师的进度
  if (!analysisStore.isAnalyzing) return 0
  
  // 根据当前步骤和分析师计算进度
  const analystIndex = form.value.analysts.indexOf(analystId)
  if (analystIndex === -1) return 0
  
  const baseProgress = (currentStep.value - 1) * 100 / totalSteps.value
  const stepProgress = analysisStore.analysisProgress - baseProgress
  
  // 当前活跃的分析师显示实时进度
  if (isAnalystActive(analystId)) {
    return Math.min(100, stepProgress * totalSteps.value)
  }
  
  // 已完成的分析师显示100%
  const currentAnalystIndex = Math.floor((currentStep.value - 1) % form.value.analysts.length)
  if (analystIndex < currentAnalystIndex) {
    return 100
  }
  
  return 0
}

const isAnalystActive = (analystId: string) => {
  if (!analysisStore.isAnalyzing) return false
  const currentAnalystIndex = Math.floor((currentStep.value - 1) % form.value.analysts.length)
  return form.value.analysts[currentAnalystIndex] === analystId
}



const getCurrentStepName = () => {
  const steps = [
    t('common.analysisSteps.dataCollection'),
    t('common.analysisSteps.technicalAnalysis'),
    t('common.analysisSteps.fundamentalAnalysis'),
    t('common.analysisSteps.sentimentAnalysis'),
    t('common.analysisSteps.riskAssessment'),
    t('common.analysisSteps.comprehensiveEvaluation'),
    t('common.analysisSteps.reportGeneration')
  ]
  return steps[currentStep.value - 1] || t('common.analysisSteps.preparing')
}

// 工具配置相关方法
const openScopeConfig = (scopeId: string, scope: any) => {
  configScopeId.value = scopeId
  configScopeName.value = scope.name
  currentScopeConfig.value = scopeConfigs.value[scopeId] || {}
  showToolConfig.value = true
}

const closeToolConfig = () => {
  showToolConfig.value = false
}

const saveToolConfig = (config: { tools: string[], dataSources: string[] }) => {
  // 保存配置到scopeConfigs
  scopeConfigs.value[configScopeId.value] = config
  // console.log('Tool config saved:', configScopeId.value, config)
}

// 处理AnalysisScopeSelector的scopeConfigs更新事件
const handleScopeConfigsUpdate = (newConfigs: Record<string, any>) => {
  scopeConfigs.value = newConfigs
  // console.log('🔄 [Home] scopeConfigs updated from AnalysisScopeSelector:', newConfigs)
}

const handleAnalysisStart = async () => {
  // console.log('🚀 Starting analysis:', {
  //   symbol: form.value.symbol,
  //   llmProvider: form.value.llmProvider,
  //   llmModel: form.value.llmModel,
  //   depth: form.value.depth,
  //   analysisScopes: form.value.analysisScopes
  // })
  
  // 检查必填字段
  if (!form.value.symbol) {
    consoleMessageService.addMessage('error', '请选择分析标的')
    return
  }
  
  if (!form.value.llmProvider || !form.value.llmModel) {
    consoleMessageService.addMessage('error', t('validation.selectProvider'))
    return
  }
  
  if (!form.value.depth) {
    consoleMessageService.addMessage('error', t('validation.selectDepth'))
    return
  }
  
  if (!form.value.analysisScopes || form.value.analysisScopes.length === 0) {
    consoleMessageService.addMessage('error', t('validation.selectScopes'))
    return
  }
  
  // 使用分析配置服务验证和转换
  try {
    // console.log('Transforming params...')
    
    // 【DEBUG】检查表单中的analysisScopes
    // console.log('🔍 [DEBUG] Home.vue 表单状态:')
    // console.log('  - form.value.analysisScopes:', form.value.analysisScopes)
    // console.log('  - form.value.analysisScopes类型:', typeof form.value.analysisScopes)
    // console.log('  - form.value.analysisScopes长度:', form.value.analysisScopes?.length)
    // console.log('  - scopeConfigs.value:', scopeConfigs.value)
    // console.log('  - scopeConfigs中的工具数:', Object.values(scopeConfigs.value).reduce((acc, config: any) => acc + (config.tools?.length || 0), 0))
    
    const apiParams = await analysisConfigService.transformToApiParams({
      marketType: form.value.marketType,
      symbol: form.value.symbol,
      timeframe: form.value.timeframe,
      depth: form.value.depth,
      analysisScopes: form.value.analysisScopes,
      llmProvider: form.value.llmProvider,
      llmModel: form.value.llmModel,
      scopeConfigs: scopeConfigs.value  // Phase 2: 传递工具配置
    })
    
    // console.log('Starting analysis with API params:', apiParams)
    await analysisStore.startAnalysis(apiParams)
    // console.log('Analysis started successfully')
  } catch (error: any) {
    console.error('Error in handleAnalysisStart:', error)
    if (error.validation) {
      // 处理验证错误
      console.error('Validation errors:', error.validation.errors)
      // 可以显示错误提示
    } else {
      console.error('Failed to start analysis:', error)
    }
    
    // 确保分析状态被重置
    analysisStore.isAnalyzing = false
  }
}

const handleAnalysisStop = () => {
  analysisStore.stopAnalysis()
}

// 查看历史记录详情
const viewHistoryDetail = (history: any) => {
  // 直接打开分析详情模态框，不进行页面跳转
  selectedAnalysisForDetail.value = history
  showAnalysisDetailModal.value = true
}

// 关闭分析详情模态框
const closeAnalysisDetailModal = () => {
  showAnalysisDetailModal.value = false
  selectedAnalysisForDetail.value = null
}

// 处理分析详情模态框的导出事件
const handleAnalysisDetailExport = (analysis: any) => {
  // 这里可以添加导出逻辑，或者让模态框自己处理
  // console.log('Export analysis:', analysis)
}


// 删除了流程画布组件引用


const copyResult = async () => {
  if (analysisStore.currentResult) {
    const resultText = JSON.stringify(analysisStore.currentResult, null, 2)
    await navigator.clipboard.writeText(resultText)
    // 可以添加一个提示
    // Success message copied to clipboard
  }
}

// 处理配置更新
const handleConfigUpdate = (updates: Partial<typeof form.value>) => {
  Object.assign(form.value, updates)
}


// 处理LLM提供商变化
async function handleProviderChange(providerId: string | null) {
  // 立即清空模型选择，避免旧值在新options中找不到导致undefined
  form.value.llmModel = ''
  
  if (providerId && providerId !== '') {
    // 加载该提供商的模型列表
    const models = await llmDetectionService.getModelsForProvider(providerId)
    currentProviderModels.value = models
    
    // 不自动选择模型，让用户主动选择
  } else {
    // 清空模型选择
    currentProviderModels.value = []
  }
}



const getLLMDescription = (provider: string) => {
  // 直接使用 providers.json 中的翻译键，这样会响应语言切换
  const providerKey = `providers.${provider}.description`
  const translatedDesc = t(providerKey)
  
  // 如果翻译键存在且不等于键本身，返回翻译后的描述
  if (translatedDesc !== providerKey) {
    return translatedDesc
  }
  
  // Fallback：从 availableLLMProviders 中获取或使用默认值
  const selectedProvider = availableLLMProviders.value.find(p => p.id === provider)
  if (selectedProvider) {
    return selectedProvider.description
  }
  
  return t('common.providerCapabilities.unknown')
}


const getModelDescription = (modelId: string | null) => {
  if (!modelId) return ''
  const model = currentProviderModels.value.find(m => m.id === modelId)
  return model?.description || ''
}


// 初始化
// 时间更新已移至 MainLayout

// 页面初始化
onMounted(async () => {
  // 初始化主题
  // initTheme()
  
  // 初始化LLM检测服务
  try {
    await llmDetectionService.initialize()
    availableLLMProviders.value = await llmDetectionService.getAvailableProviders()
    
    // 不自动设置推荐配置，让用户主动选择
  } catch (error) {
    console.error('初始化LLM服务失败:', error)
  }
  
  // 初始化成本数据
  try {
    await costStore.initializeApiData()
    // console.log('✅ 成本数据初始化完成')
  } catch (error) {
    console.error('初始化成本数据失败:', error)
  }
  
  await nextTick()
  
  // 处理来自成本监控页面的跳转
  if (route.query.showHistory === 'true' && route.query.historyId) {
    const historyId = route.query.historyId as string
    const history = analysisStore.analysisHistory.find(h => h.id === historyId)
    if (history) {
      // 切换到历史记录标签页查看完整分析
      activeTab.value = 'history'
    }
  }
})
</script>

<style scoped>
/* 专业分析师卡片 - 紧凑版本 */
.analyst-card--professional--compact {
  @apply p-2 rounded-lg cursor-pointer transition-all duration-200;
  background: var(--ft-surface);
  border: 1px solid var(--ft-border);
  position: relative;
  overflow: hidden;
}

.analyst-card--professional--compact:hover {
  transform: translateY(-1px);
  box-shadow: var(--ft-shadow-md);
  border-color: var(--ft-border-light);
}

.analyst-card--selected {
  background: var(--ft-surface-light);
  border-color: var(--ft-primary);
  box-shadow: var(--ft-glow-primary);
}

.analyst-card--professional--compact::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, transparent, rgba(0, 212, 255, 0.1), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.analyst-card--professional--compact:hover::before {
  opacity: 1;
}

/* 悬停特效优化 */
.hover--glow {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.hover--glow:hover {
  box-shadow: var(--ft-glow-primary);
  transform: translateY(-2px) scale(1.02);
  z-index: 100;
}

/* 分析师卡片悬停特效 */
.analyst-card--professional--compact:hover {
  position: relative;
  z-index: 100;
}

/* 活跃分析师卡片 */
.analyst-card--active {
  border-color: var(--od-primary) !important;
  background: var(--od-background-light) !important;
}

/* 分析师进度环 */
.analyst-progress-ring {
  position: absolute;
  inset: -2px;
  pointer-events: none;
}

/* 分析师进度条容器 */
.analyst-progress-bar-container {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--od-border);
  overflow: hidden;
}

/* 分析师进度条填充 */
.analyst-progress-bar-fill {
  height: 100%;
  background: var(--gradient-od-primary);
  transition: width 0.3s ease;
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.6);
}

/* 分析深度卡片悬停特效 */
.depth-card:hover {
  position: relative;
  z-index: 50;
}

/* 现代化分析师徽章 */
.analyst-badge-modern {
  @apply relative w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-300 overflow-hidden;
  background: var(--ft-surface-light);
  border: 1px solid var(--ft-border);
}

.analyst-badge__gradient-bg {
  @apply absolute inset-0 opacity-0 transition-all duration-300;
}

.analyst-badge__icon {
  @apply relative z-10 transition-all duration-300;
  color: var(--ft-text-muted);
}

/* 专业分析师徽章（原版，保留） */
.analyst-badge {
  @apply relative w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-300;
  background: var(--ft-surface-light);
  border: 1px solid var(--ft-border);
}

.analyst-badge__border {
  @apply absolute inset-0 rounded-lg border-2 opacity-0 transition-all duration-300;
  border-color: transparent;
}

/* 现代化分析师类别特定样式 */
.analyst-badge-modern.analyst-badge--technical.analyst-badge--selected .analyst-badge__gradient-bg {
  background: linear-gradient(135deg, var(--ft-analyst-tech), rgba(0, 200, 81, 0.8));
  opacity: 1;
}

.analyst-badge-modern.analyst-badge--fundamental.analyst-badge--selected .analyst-badge__gradient-bg {
  background: linear-gradient(135deg, var(--ft-analyst-fundamental), rgba(25, 118, 210, 0.8));
  opacity: 1;
}

.analyst-badge-modern.analyst-badge--sentiment.analyst-badge--selected .analyst-badge__gradient-bg {
  background: linear-gradient(135deg, var(--ft-analyst-sentiment), rgba(212, 175, 55, 0.8));
  opacity: 1;
}

.analyst-badge-modern.analyst-badge--risk.analyst-badge--selected .analyst-badge__gradient-bg {
  background: linear-gradient(135deg, var(--ft-analyst-risk), rgba(211, 47, 47, 0.8));
  opacity: 1;
}

.analyst-badge-modern.analyst-badge--market.analyst-badge--selected .analyst-badge__gradient-bg {
  background: linear-gradient(135deg, var(--ft-analyst-market), rgba(255, 111, 0, 0.8));
  opacity: 1;
}

.analyst-badge-modern.analyst-badge--selected .analyst-badge__icon {
  color: white;
  transform: scale(1.05);
}

.analyst-badge-modern.analyst-badge--selected {
  border-color: currentColor;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.3);
}

/* 原版分析师类别特定样式（保留） */
.analyst-badge--technical.analyst-badge--selected {
  background: var(--ft-analyst-tech);
  box-shadow: var(--ft-glow-success);
}

.analyst-badge--fundamental.analyst-badge--selected {
  background: var(--ft-analyst-fundamental);
  box-shadow: var(--ft-glow-info);
}

.analyst-badge--sentiment.analyst-badge--selected {
  background: var(--ft-analyst-sentiment);
  box-shadow: var(--ft-glow-primary);
}

.analyst-badge--risk.analyst-badge--selected {
  background: var(--ft-analyst-risk);
  box-shadow: var(--ft-glow-error);
}

.analyst-badge--market.analyst-badge--selected {
  background: var(--ft-analyst-market);
  box-shadow: var(--ft-glow-warning);
}

.analyst-badge--selected .analyst-badge__icon {
  color: white;
  transform: scale(1.1);
}

.analyst-badge--selected .analyst-badge__border {
  opacity: 1;
  border-color: currentColor;
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% {
    transform: scale(1);
    opacity: 0.7;
  }
  50% {
    transform: scale(1.05);
    opacity: 1;
  }
}

/* 分析深度卡片 - 紧凑版 */
.depth-card--compact {
  @apply p-2 rounded-md cursor-pointer transition-all duration-200 text-center;
  background: var(--ft-surface);
  border: 1px solid var(--ft-border);
}

.depth-card--compact:hover {
  border-color: var(--ft-border-light);
  background: var(--ft-surface-light);
}

.depth-card--compact.depth-card--selected {
  background: var(--ft-interactive-active);
  border-color: var(--ft-primary);
  box-shadow: var(--ft-glow-primary);
}

.depth-card--compact .depth-card__icon {
  @apply flex justify-center mb-1 transition-all duration-200;
  color: var(--ft-text-muted);
}

.depth-card--compact.depth-card--selected .depth-card__icon {
  color: var(--ft-primary);
}

.depth-card--compact .depth-card__label {
  @apply text-xs font-medium;
  color: var(--ft-text-primary);
}

.depth-card--compact.depth-card--selected .depth-card__label {
  color: var(--ft-primary);
}

/* 原版分析深度卡片（保留用于其他地方） */
.depth-card {
  @apply p-3 rounded-lg cursor-pointer transition-all duration-200 text-center;
  background: var(--ft-surface);
  border: 1px solid var(--ft-border);
}

.depth-card:hover {
  border-color: var(--ft-border-light);
  background: var(--ft-surface-light);
  transform: translateY(-1px);
}

.depth-card--selected {
  background: var(--ft-interactive-active);
  border-color: var(--ft-primary);
  box-shadow: var(--ft-glow-primary);
}

.depth-card__icon {
  @apply flex justify-center mb-2 transition-all duration-200;
  color: var(--ft-text-muted);
}

.depth-card--selected .depth-card__icon {
  color: var(--ft-primary);
  transform: scale(1.1);
}

.depth-card__text {
  @apply space-y-1;
}

.depth-card__label {
  @apply text-xs font-medium;
  color: var(--ft-text-primary);
}

.depth-card__time {
  @apply text-xs;
  color: var(--ft-text-muted);
}

.depth-card--selected .depth-card__label {
  color: var(--ft-primary);
}

/* 专业分析师卡片 */
.analyst-card--professional {
  @apply p-3 rounded-lg cursor-pointer transition-all duration-200 flex items-center justify-between;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
}

/* 分析师状态卡片 */
.analyst-status-card--professional {
  @apply p-2 rounded-lg;
  background: var(--od-background-light);
}

/* LLM介绍卡片 - 紧凑版本 */
.llm-intro-card--professional--compact {
  @apply p-2 rounded-md;
  background: var(--ft-background-light);
  border: 1px solid var(--ft-border);
}

/* LLM介绍卡片 - 单行内联版本 */
.llm-intro-card--professional--inline {
  @apply px-2 py-1 rounded;
  background: var(--ft-background-light);
  border: 1px solid var(--ft-border);
}

/* 表单组紧凑间距 */
.form-group {
  @apply space-y-1;
}

.form-group:not(:last-child) {
  @apply mb-1.5;
}

/* 紧凑型卡片 */
.card--od--refined--compact {
  @apply rounded-lg;
  background: var(--od-surface);
  border: 1px solid var(--od-border);
  box-shadow: var(--shadow-od-sm);
}

/* 紧凑型区块头部 */
.section__header--od--compact {
  @apply flex items-center justify-between p-3 border-b;
  border-color: var(--od-border);
}

/* 紧凑型区块内容 */
.section__content--od {
  @apply p-3;
}

/* 专业进度条 */
.progress-container--professional {
  @apply relative w-full h-2 rounded-full overflow-hidden;
  background: var(--od-background-light);
}

.progress-bar--professional {
  @apply h-full rounded-full transition-all duration-500 ease-out;
  background: var(--gradient-od-primary);
  position: relative;
  max-width: 100%;
  box-sizing: border-box;
}

.progress-glow--professional {
  @apply absolute inset-0 rounded-full opacity-50;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  animation: shimmer 2s infinite;
}

/* 成本监控进度条样式 */
.cost-progress-container {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.cost-progress-track {
  position: relative;
  width: 100%;
  height: 8px;
  background: var(--od-background-light);
  border-radius: 9999px;
  overflow: hidden;
  box-sizing: border-box;
}

.cost-progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(to right, #3B82F6, #10B981);
  border-radius: 9999px;
  transition: width 500ms ease;
  box-sizing: border-box;
  max-width: 100%;
}

/* 分析进度条样式 */
.analysis-progress-container {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.analysis-progress-track {
  position: relative;
  width: 100%;
  height: 8px;
  background: var(--od-background-light);
  border-radius: 9999px;
  overflow: hidden;
  box-sizing: border-box;
}

.analysis-progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--gradient-od-primary);
  border-radius: 9999px;
  transition: width 500ms ease-out;
  box-sizing: border-box;
  max-width: 100%;
}

.analysis-progress-glow {
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  opacity: 0.5;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* 结果容器 */
.result-container--professional {
  @apply p-4 rounded-lg;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
}

/* 统一滚动条 */
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

/* 精致动画效果 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式调整 */
@media (max-width: 1024px) {
  .grid-cols-12 {
    grid-template-columns: 1fr;
  }
  
  .h-full {
    min-height: 300px;
  }
}

/* 移动端进度条修复 */
@media (max-width: 768px) {
  /* 修复分析进度条溢出 */
  .analysis-progress-container {
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
  }
  
  .analysis-progress-track {
    width: calc(100% - 0px) !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  .analysis-progress-fill {
    max-width: 100% !important;
    transform: none !important;
    box-shadow: none !important;
  }
  
  .analysis-progress-glow {
    display: none !important; /* 移动端禁用光晕效果 */
  }
  
  /* 修复成本监控进度条溢出 */
  .cost-progress-container {
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
  }
  
  .cost-progress-track {
    width: calc(100% - 0px) !important; /* 确保不超出容器 */
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  .cost-progress-fill {
    max-width: 100% !important;
    transform: none !important; /* 禁用可能导致溢出的变换 */
    box-shadow: none !important; /* 移除阴影避免视觉溢出 */
  }
  
  /* 确保所有进度条父容器不溢出 */
  .space-y-2,
  .section__content--od,
  .card--od--refined {
    overflow-x: hidden !important;
    max-width: 100% !important;
  }
  
  /* 移除进度条区域的滚动条 */
  .cost-progress-container {
    overflow: hidden !important;
  }
  
  /* 确保包含进度条的父容器不产生滚动条 */
  .space-y-2:has(.cost-progress-container) {
    overflow: hidden !important;
  }
  
  /* 成本监控区域在移动端不需要内部滚动 */
  .section__content--od:has(.cost-progress-container) {
    overflow: visible !important;
  }
  
  /* 移除分析进度条区域的滚动条 */
  .analysis-progress-container {
    overflow: hidden !important;
  }
  
  /* 确保包含分析进度条的父容器不产生滚动条 */
  .px-4.py-3:has(.analysis-progress-container) {
    overflow: hidden !important;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

/* 版本选择器样式 */
.version-selector-btn {
  @apply p-2 rounded-lg cursor-pointer transition-all duration-300;
  background: var(--od-surface);
  border: 1px solid var(--od-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-height: 70px;
}

.version-selector-btn:hover {
  border-color: var(--od-primary);
  background: var(--od-surface-light);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}

.version-selector-btn--active {
  background: linear-gradient(135deg, var(--od-primary), #fbbf24);
  border-color: var(--od-primary);
  color: #0f172a;
  box-shadow: 0 4px 20px rgba(245, 158, 11, 0.4);
}

.version-selector-btn--active:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 25px rgba(245, 158, 11, 0.5);
}

.version-icon {
  font-size: 18px;
  margin-bottom: 4px;
}

.version-selector-btn--active .version-icon {
  animation: bounce 2s infinite;
}

.version-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.version-name {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 1px;
  color: var(--od-text-primary);
}

.version-selector-btn--active .version-name {
  color: #0f172a;
  font-weight: 700;
}

.version-desc {
  font-size: 9px;
  color: var(--od-text-muted);
  line-height: 1.2;
}

.version-selector-btn--active .version-desc {
  color: rgba(15, 23, 42, 0.8);
}

@keyframes bounce {
  0%, 20%, 53%, 80%, 100% {
    transform: translateY(0);
  }
  40%, 43% {
    transform: translateY(-4px);
  }
  70% {
    transform: translateY(-2px);
  }
  90% {
    transform: translateY(-1px);
  }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .grid-cols-4 {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .lg\:grid-cols-6 {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .version-selector-btn {
    min-height: 60px;
    padding: 8px;
  }
  
  .version-icon {
    font-size: 16px;
  }
  
  .version-name {
    font-size: 10px;
  }
  
  .version-desc {
    font-size: 8px;
  }
}

@media (max-width: 480px) {
  .grid-cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .lg\:grid-cols-6 {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .version-selector-btn {
    min-height: 50px;
    padding: 6px;
  }
  
  .version-desc {
    display: none;
  }
}

/* 分析运行时标签禁用样式 */
.tab--od--refined--disabled {
  opacity: 0.5 !important;
  cursor: not-allowed !important;
  pointer-events: none !important;
}

.tab--od--refined--disabled:hover {
  background: none !important;
  transform: none !important;
}
</style>
