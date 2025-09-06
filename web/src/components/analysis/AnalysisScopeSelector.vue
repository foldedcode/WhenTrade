<template>
  <div class="form-group">
    <label class="block text-xs font-medium mb-1.5" style="color: var(--od-text-secondary)">
      {{ $t('analysis.analysisScope') }}
    </label>
    <!-- 专业金融终端风格的紧凑网格布局 -->
    <div class="scope-grid--terminal">
      <div
        v-for="scope in availableScopes"
        :key="scope.id"
        class="scope-card--terminal"
        :class="{ 
          'scope-card--terminal--selected': modelValue.includes(scope.id),
          'scope-card--terminal--disabled': disabled
        }"
        @click="toggleScope(scope.id)"
      >
        <!-- 状态指示器 -->
        <div class="scope-indicator--terminal" :class="{ 'active': modelValue.includes(scope.id) }">
          <div class="indicator-dot"></div>
        </div>
        
        <!-- 内容区域 -->
        <div class="scope-content--terminal">
          <div
            class="scope-text--terminal"
            :title="`${$t(scope.name)} - ${$t(scope.description)}`"
          >
            <span class="scope-name--terminal">{{ $t(scope.name) }}</span>
            <span class="scope-desc--terminal"> - {{ $t(scope.description) }}</span>
          </div>
        </div>
        
        <!-- 配置按钮和选中标记 -->
        <div class="scope-actions">
          <!-- 配置按钮 -->
          <button 
            v-if="modelValue.includes(scope.id)"
            class="config-btn--terminal"
            :disabled="disabled"
            @click.stop="openConfig(scope)"
            title="配置工具"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 15.5C13.933 15.5 15.5 13.933 15.5 12C15.5 10.067 13.933 8.5 12 8.5C10.067 8.5 8.5 10.067 8.5 12C8.5 13.933 10.067 15.5 12 15.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 2V6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 18V22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M4.93 4.93L7.76 7.76" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M16.24 16.24L19.07 19.07" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 12H6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M18 12H22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M4.93 19.07L7.76 16.24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M16.24 7.76L19.07 4.93" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          
          <!-- 选中标记 -->
          <div v-if="modelValue.includes(scope.id)" class="scope-check--terminal">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2.5 6L5 8.5L9.5 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 选择状态栏 -->
    <div class="scope-status--terminal">
      <div class="status-left">
        <span class="status-label">{{ $t('analysis.selected') }}:</span>
        <span class="status-count">{{ modelValue.length }}/{{ availableScopes.length }}</span>
      </div>
      <div v-if="validationError" class="status-error">
        {{ validationError }}
      </div>
    </div>
    
    <!-- 配置弹窗 - 使用 Teleport 将弹窗挂载到 body -->
    <Teleport to="body">
      <div v-if="showConfigModal" class="config-modal-overlay" @click.self="closeConfig">
        <div class="config-modal">
        <div class="modal-header">
          <h3>配置{{ currentScope ? $t(currentScope.name) : '' }}</h3>
          <button class="close-btn" @click="closeConfig">×</button>
        </div>
        
        <div class="modal-body">
          <!-- 工具选择 -->
          <div class="config-section">
            <h4>{{ $t('analysis.config.tools') }}:</h4>
            <div v-for="tool in availableTools" :key="tool.id" class="config-option">
              <input 
                type="checkbox" 
                :value="tool.id"
                v-model="tempConfig.tools"
                :id="`tool-${tool.id}`"
              />
              <label 
                class="clickable-label"
                :for="`tool-${tool.id}`"
              >
                {{ getToolDisplayName(tool) }}
              </label>
            </div>
            <div v-if="!availableTools.length" class="empty-message">{{ $t('analysis.config.unconfigured') }}</div>
          </div>
          
          <!-- 数据源选择 -->
          <div class="config-section">
            <h4>{{ $t('analysis.config.data') }}:</h4>
            <div v-for="source in availableDataSources" :key="source.id" class="config-option">
              <input 
                type="checkbox" 
                :value="source.id"
                v-model="tempConfig.dataSources"
                :id="`source-${source.id}`"
              />
              <span 
                @click="toggleDataSource(source.id)"
                class="clickable-label"
                :for="`source-${source.id}`"
              >
                {{ getDataSourceDisplayName(source) }}
              </span>
            </div>
            <div v-if="!availableDataSources.length" class="empty-message">{{ $t('analysis.config.unconfigured') }}</div>
          </div>
        </div>
        
        <div class="modal-footer">
          <div class="footer-left">
            <button class="btn-reset" @click="resetConfig">重置</button>
            <button class="btn-select-all" @click="selectAll">全选</button>
          </div>
          <div class="flex gap-2">
            <button class="btn-confirm" @click="saveConfig">确定</button>
            <button class="btn-cancel" @click="closeConfig">取消</button>
          </div>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { AnalysisScope } from '@/types/analysis'
import type { MarketType } from '@/types/market'
import { analysisConfigService } from '@/services/analysis-config.service'
import { useI18n } from 'vue-i18n'

// 扩展的分析范围类型，包含工具配置
interface ExtendedAnalysisScope extends AnalysisScope {
  availableTools?: Array<{id: string, name: string}>
  availableDataSources?: Array<{id: string, name: string}>
}

interface Props {
  modelValue: string[]
  marketType: MarketType
  maxSelection?: number
  scopeConfigs: Record<string, any>
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string[]): void
  (e: 'update:scopeConfigs', value: Record<string, any>): void
  (e: 'configure', scopeId: string, scope: ExtendedAnalysisScope): void
}

const props = withDefaults(defineProps<Props>(), {
  maxSelection: 5
})

const emit = defineEmits<Emits>()
const { t } = useI18n()

const availableScopes = ref<AnalysisScope[]>([])
const loading = ref(false)

// 配置相关状态
const showConfigModal = ref(false)
const currentScope = ref<ExtendedAnalysisScope | null>(null)
const tempConfig = ref({
  tools: [] as string[],
  dataSources: [] as string[]
})

// scopeConfigs现在来自父组件的props

// 真实数据源（从当前scope获取）
const availableTools = ref<Array<{id: string, name: string}>>([])
const availableDataSources = ref<Array<{id: string, name: string}>>([])

// 从后端API加载scope配置
const loadScopeConfig = async (scopeId: string) => {
  try {
    // 调用后端API获取工具和数据源数据
    const response = await fetch(`/api/v1/config/analysis-tools/${scopeId}`)
    if (response.ok) {
      const data = await response.json()
      availableTools.value = data.tools || []
      // 直接使用API返回的数据源列表
      availableDataSources.value = data.data_sources || []
    } else {
      console.error('Failed to load scope tools:', response.statusText)
      availableTools.value = []
      availableDataSources.value = []
    }
  } catch (error) {
    console.error('Error loading scope config:', error)
    availableTools.value = []
    availableDataSources.value = []
  }
}

// 数据源现在直接从API获取，不需要动态计算

// 全选方法 - 同时选择所有工具和数据源
const selectAll = () => {
  tempConfig.value.tools = availableTools.value.map(tool => tool.id)
  tempConfig.value.dataSources = availableDataSources.value.map(source => source.id)
}

// 配置相关方法
const openConfig = async (scope: ExtendedAnalysisScope) => {
  if (props.disabled) return
  
  currentScope.value = scope
  
  // 从后端API获取真实的工具和数据源数据
  await loadScopeConfig(scope.id)
  
  // 设置临时配置，从现有配置中读取
  const existing = props.scopeConfigs[scope.id] || {}
  tempConfig.value = {
    tools: existing.tools || [],
    dataSources: existing.dataSources || []
  }
  
  // 防止背景滚动
  document.body.style.overflow = 'hidden'
  showConfigModal.value = true
}

// 关闭配置弹窗
const closeConfig = () => {
  showConfigModal.value = false
  currentScope.value = null
  // 恢复滚动
  document.body.style.overflow = ''
}

// 重置配置
const resetConfig = () => {
  tempConfig.value = {
    tools: [],
    dataSources: []
  }
}

// 保存配置
const saveConfig = async () => {
  if (currentScope.value) {
    const newConfigs = {
      ...props.scopeConfigs,
      [currentScope.value.id]: { ...tempConfig.value }
    }
    emit('update:scopeConfigs', newConfigs)
    
    // 确保更新完全传播到父组件
    await nextTick()
    
    // console.log('Saved config for scope:', currentScope.value.id, tempConfig.value)
  }
  closeConfig()
}



// 切换数据源选择
const toggleDataSource = (sourceId: string) => {
  const currentSources = [...tempConfig.value.dataSources]
  const index = currentSources.indexOf(sourceId)
  if (index > -1) {
    currentSources.splice(index, 1)
  } else {
    currentSources.push(sourceId)
  }
  tempConfig.value.dataSources = currentSources
}

// 获取工具显示名称
const getToolDisplayName = (tool: any) => {
  // 备用中英文映射 - 基于截图中的工具名称
  const toolNameMap: Record<string, Record<string, string>> = {
    'crypto_price': { 'zh-CN': '加密货币价格', 'en-US': 'Crypto Price' },
    'indicators': { 'zh-CN': '技术指标', 'en-US': 'Technical Indicators' },
    'market_data': { 'zh-CN': '实时市场数据', 'en-US': 'Real-time Market Data' },
    'historical_data': { 'zh-CN': '历史价格数据', 'en-US': 'Historical Price Data' },
    'market_metrics': { 'zh-CN': '市场指标', 'en-US': 'Market Metrics' },
    'trending': { 'zh-CN': '热门币种', 'en-US': 'Trending Coins' },
    'fear_greed': { 'zh-CN': '恐惧贪婪指数', 'en-US': 'Fear & Greed Index' },
    'finnhub_news': { 'zh-CN': 'FinnHub新闻', 'en-US': 'FinnHub News' },
    'reddit_sentiment': { 'zh-CN': 'Reddit情绪分析', 'en-US': 'Reddit Sentiment' },
    'sentiment_batch': { 'zh-CN': '批量情绪分析', 'en-US': 'Batch Sentiment' }
  }
  
  // 获取当前语言
  const locale = localStorage.getItem('when-trade-locale') || 'zh-CN'
  
  // 尝试从备用映射获取
  if (toolNameMap[tool.id] && toolNameMap[tool.id][locale]) {
    return toolNameMap[tool.id][locale]
  }
  
  // 尝试从翻译中获取
  const translationKey = `analysis.tools.${tool.id}`
  const translated = t(translationKey)
  
  if (translated !== translationKey) {
    return translated
  }
  
  // 如果没有翻译，使用display_name
  if (tool.display_name) {
    return tool.display_name
  }
  
  // 最后使用原始名称
  return tool.name
}

// 获取数据源显示名称
const getDataSourceDisplayName = (source: any) => {
  // 备用数据源映射
  const dataSourceMap: Record<string, Record<string, string>> = {
    'coingecko': { 'zh-CN': 'CoinGecko', 'en-US': 'CoinGecko' },
    'yahoo_finance': { 'zh-CN': '雅虎财经', 'en-US': 'Yahoo Finance' },
    'finnhub': { 'zh-CN': 'FinnHub', 'en-US': 'FinnHub' },
    'reddit': { 'zh-CN': 'Reddit', 'en-US': 'Reddit' },
    'alternative_me': { 'zh-CN': 'Alternative.me', 'en-US': 'Alternative.me' },
    'alternative.me': { 'zh-CN': 'Alternative.me', 'en-US': 'Alternative.me' }
  }
  
  // 获取当前语言
  const locale = localStorage.getItem('when-trade-locale') || 'zh-CN'
  
  // 尝试从备用映射获取
  if (dataSourceMap[source.id] && dataSourceMap[source.id][locale]) {
    return dataSourceMap[source.id][locale]
  }
  
  // 尝试从翻译中获取
  const translationKey = `analysis.dataSources.${source.id}`
  const translated = t(translationKey)
  if (translated !== translationKey) {
    return translated
  }
  
  // 如果没有翻译，使用display_name
  if (source.display_name) {
    return source.display_name
  }
  
  // 最后使用原始名称
  return source.name
}

// 验证错误信息
const validationError = computed(() => {
  if (props.modelValue.length === 0) {
    return t('analysis.validation.selectScope')
  }
  if (props.modelValue.length > props.maxSelection) {
    return t('analysis.validation.tooManyScopes', { max: props.maxSelection })
  }
  return ''
})

// 切换选择状态
const toggleScope = (scopeId: string) => {
  if (props.disabled) return
  
  const currentSelection = [...props.modelValue]
  const index = currentSelection.indexOf(scopeId)
  
  // console.log('🔍 [DEBUG] AnalysisScopeSelector 切换:', {
  //   scopeId,
  //   currentSelection: [...currentSelection],
  //   action: index > -1 ? '取消选择' : '添加选择'
  // })
  
  if (index > -1) {
    // 取消选择
    currentSelection.splice(index, 1)
  } else {
    // 添加选择，检查数量限制
    if (currentSelection.length < props.maxSelection) {
      currentSelection.push(scopeId)
    } else {
      // 达到上限，不做操作但可以显示提示
      return
    }
  }
  
  // console.log('🎯 [DEBUG] AnalysisScopeSelector 更新后:', currentSelection)
  emit('update:modelValue', currentSelection)
}

// 加载可用的分析范围
const loadAvailableScopes = async () => {
  if (!props.marketType) return
  
  loading.value = true
  try {
    availableScopes.value = await analysisConfigService.getAnalysisScopes(props.marketType)
    
    // 过滤掉不再可用的选择
    const availableIds = availableScopes.value.map(s => s.id)
    const filteredSelection = props.modelValue.filter(id => availableIds.includes(id))
    
    if (filteredSelection.length !== props.modelValue.length) {
      emit('update:modelValue', filteredSelection)
    }
  } catch (error) {
    console.error('Failed to load analysis scopes:', error)
  } finally {
    loading.value = false
  }
}


// 监听市场类型变化
watch(() => props.marketType, () => {
  loadAvailableScopes()
}, { immediate: true })

</script>

<style scoped>
/* 专业金融终端风格 - 网格布局 */
.scope-grid--terminal {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.375rem;
  margin-bottom: 0.625rem;
}

/* 范围卡片 - 超紧凑专业设计 */
.scope-card--terminal {
  position: relative;
  padding: 0.5rem;
  overflow: hidden;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

/* 基础悬停状态 - 仅用于非选中项 */
.scope-card--terminal:hover:not(.scope-card--terminal--selected) {
  background: rgba(78, 201, 176, 0.03);
  border-color: rgba(78, 201, 176, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(78, 201, 176, 0.1);
}

/* 选中状态 - 使用主题色，优先级最高 */
.scope-card--terminal.scope-card--terminal--selected {
  background: linear-gradient(135deg, 
    rgba(78, 201, 176, 0.05) 0%, 
    rgba(78, 201, 176, 0.02) 100%) !important;
  border-color: var(--od-primary) !important;
  box-shadow: 0 0 0 1px rgba(78, 201, 176, 0.2) inset, 
              0 0 8px rgba(78, 201, 176, 0.15) !important;
}

/* 选中项的悬停增强效果 */
.scope-card--terminal.scope-card--terminal--selected:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px rgba(78, 201, 176, 0.3) inset, 
              0 0 12px rgba(78, 201, 176, 0.25),
              0 2px 4px rgba(78, 201, 176, 0.1) !important;
}

/* 状态指示器 - 金融终端风格 */
.scope-indicator--terminal {
  width: 0.25rem;
  height: 1.25rem;
  background: var(--od-border);
  border-radius: 0.125rem;
  transition: all 0.2s ease;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.scope-indicator--terminal.active {
  background: linear-gradient(to bottom, var(--od-primary), var(--od-primary-light));
  box-shadow: 0 0 4px rgba(78, 201, 176, 0.5);
}

/* 移除状态指示器动画 */

@keyframes indicatorPulse {
  0%, 100% { opacity: 0.5; transform: translateY(-100%); }
  50% { opacity: 1; transform: translateY(100%); }
}

/* 内容区域 */
.scope-content--terminal {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 2;
  pointer-events: none; /* 防止阻挡父元素点击事件 */
}

/* 文本容器 */
.scope-text--terminal {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  overflow: hidden;
}

.scope-name--terminal {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--od-text-primary);
  letter-spacing: 0.025em;
  text-transform: uppercase;
  line-height: 1.2;
  white-space: nowrap;
  flex-shrink: 0;
}

.scope-card--terminal--selected .scope-name--terminal {
  color: var(--od-primary-light);
  text-shadow: 0 0 8px rgba(78, 201, 176, 0.3);
}

/* 描述文本 - 内联显示 */
.scope-desc--terminal {
  font-size: 0.5625rem;
  line-height: 1.2;
  color: var(--od-text-muted);
  display: inline;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.scope-card--terminal:hover .scope-desc--terminal {
  color: var(--od-text-secondary);
}

.scope-card--terminal--selected .scope-desc--terminal {
  color: var(--od-text-secondary);
}

/* 选中标记 - 专业风格 */
.scope-check--terminal {
  width: 1rem;
  height: 1rem;
  background: linear-gradient(135deg, var(--od-primary), var(--od-primary-light));
  border-radius: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: checkIn 0.2s ease;
  z-index: 11;
  pointer-events: none; /* 不阻挡点击 */
  box-shadow: 0 2px 4px rgba(78, 201, 176, 0.3);
}

.scope-check--terminal svg {
  color: var(--od-background);
}

/* 配置相关样式 */
.scope-actions {
  position: absolute;
  top: 50%;
  right: 0.5rem;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  z-index: 10;
}

.config-btn--terminal {
  width: 1.5rem;
  height: 1.5rem;
  background: linear-gradient(135deg, var(--od-background) 0%, var(--od-background-alt) 100%);
  border: 1px solid rgba(78, 201, 176, 0.3);
  border-radius: 0.375rem;
  color: var(--od-text-secondary);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 12;
  position: relative;
  overflow: hidden;
  pointer-events: auto;
  
  svg {
    width: 14px;
    height: 14px;
    transition: transform 0.3s ease;
  }
  
  &::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(78, 201, 176, 0.3) 0%, transparent 70%);
    transform: translate(-50%, -50%);
    transition: width 0.3s, height 0.3s;
  }
  
  &:hover {
    border-color: var(--od-primary);
    color: var(--od-primary);
    background: linear-gradient(135deg, rgba(78, 201, 176, 0.15) 0%, rgba(78, 201, 176, 0.1) 100%);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(78, 201, 176, 0.3);
    
    svg {
      transform: rotate(45deg);
    }
    
    &::before {
      width: 30px;
      height: 30px;
    }
  }
  
  &:active {
    transform: scale(0.95) translateY(-1px);
  }
}

@keyframes checkIn {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* 状态栏 - 金融数据风格 */
.scope-status--terminal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--od-border);
  border-radius: 0.375rem;
  font-size: 0.625rem;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-label {
  color: var(--od-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-count {
  color: var(--od-primary-light);
  font-weight: 600;
  font-family: 'Proto Mono', monospace;
  background: rgba(78, 201, 176, 0.1);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(78, 201, 176, 0.2);
}

.status-error {
  color: var(--od-color-error);
  font-size: 0.625rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* 响应式调整 */
@media (min-width: 1280px) {
  .scope-grid--terminal {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1279px) {
  .scope-grid--terminal {
    grid-template-columns: 1fr;
  }
  
  .scope-card--terminal {
    padding: 0.625rem;
  }
}

@media (max-width: 640px) {
  .scope-grid--terminal {
    grid-template-columns: 1fr;
  }
}

/* 动画优化 */
@media (prefers-reduced-motion: reduce) {
  .scope-card--terminal,
  .scope-indicator--terminal,
  .scope-check--terminal {
    animation: none;
    transition: none;
  }
}

/* 配置弹窗样式 */
.config-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100000;
  animation: fadeIn 0.2s;
  backdrop-filter: blur(4px);
}

.config-modal {
  position: relative;
  background: var(--od-background);
  border: 1px solid var(--od-border);
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  animation: modalFadeIn 0.3s;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(78, 201, 176, 0.1);
  margin: 20px auto;
  
  .modal-header {
    padding: 1rem;
    border-bottom: 1px solid var(--od-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h3 {
      margin: 0;
      color: var(--od-primary-light);
      font-size: 16px;
    }
    
    .close-btn {
      background: none;
      border: none;
      color: var(--od-text-secondary);
      font-size: 24px;
      cursor: pointer;
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      &:hover {
        color: var(--od-error);
      }
    }
  }
  
  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    
    .config-section {
      margin-bottom: 1.5rem;
      
      h4 {
        color: var(--od-primary-light);
        font-size: 13px;
        margin: 0 0 0.75rem 0;
        text-shadow: 0 0 4px rgba(78, 201, 176, 0.2);
      }
      
      .config-option {
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        
        input[type="checkbox"] {
          cursor: pointer;
          flex-shrink: 0;
        }
        
        .clickable-label {
          cursor: pointer;
          color: var(--od-text-primary);
          font-size: 12px;
          user-select: none;
          
          &:hover {
            color: var(--od-primary);
          }
        }
      }
      
      .empty-message {
        color: var(--od-text-muted);
        font-size: 11px;
        font-style: italic;
      }
    }
  }
  
  .modal-footer {
    padding: 1rem;
    border-top: 1px solid var(--od-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .footer-left {
      display: flex;
      align-items: center;
    }
    
    .flex {
      display: flex;
      gap: 0.5rem;
    }
    
    button {
      padding: 0.5rem 1.5rem;
      border: none;
      border-radius: 4px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
      font-family: inherit;
      
      &.btn-confirm {
        background: linear-gradient(135deg, var(--od-primary), var(--od-primary-light));
        color: var(--od-background);
        font-weight: bold;
        border: 1px solid var(--od-primary);
        box-shadow: 0 2px 4px rgba(78, 201, 176, 0.2);
        
        &:hover {
          background: linear-gradient(135deg, var(--od-primary-light), var(--od-primary));
          box-shadow: 0 4px 8px rgba(78, 201, 176, 0.3);
          transform: translateY(-1px);
        }
      }
      
      &.btn-cancel {
        background: var(--od-background-alt);
        color: var(--od-text-secondary);
        border: 1px solid var(--od-border);
        
        &:hover {
          border-color: var(--od-text-secondary);
          color: var(--od-text-primary);
        }
      }
      
      &.btn-reset {
        background: var(--od-background);
        color: var(--od-text-muted);
        border: 1px solid var(--od-border);
        
        &:hover {
          background: var(--od-error);
          color: white;
          border-color: var(--od-error);
          transform: translateY(-1px);
        }
      }
      
      &.btn-select-all {
        background: var(--od-background);
        border: 1px solid var(--od-border);
        color: var(--od-text-muted);
        margin-left: 0.5rem;  /* 与重置按钮的间距 */
        
        &:hover {
          background: rgba(74, 222, 128, 0.2);
          color: white;
          border-color: var(--od-primary-light);
          transform: translateY(-1px);
        }
      }
    }
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes glow {
  from {
    box-shadow: 0 0 8px rgba(78, 201, 176, 0.6), inset 0 0 4px rgba(156, 220, 254, 0.2);
  }
  to {
    box-shadow: 0 0 12px rgba(78, 201, 176, 0.8), inset 0 0 6px rgba(156, 220, 254, 0.3);
  }
}

/* 禁用状态样式 */
.scope-card--terminal--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.scope-card--terminal--disabled:hover {
  transform: none;
  background: var(--od-background-alt);
  border-color: var(--od-border);
  box-shadow: none;
}

.config-btn--terminal:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

</style>
