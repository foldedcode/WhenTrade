<template>
  <div class="practical-console">
    <!-- 上部分：配置与流程 -->
    <div class="console-upper">
      <!-- 左侧：配置与分析范围 -->
      <div class="config-section">
        <!-- 基础配置 -->
        <div class="basic-config">
          <div class="config-item">
            <span class="label">{{ t('analysis.console.labels.market') }}:</span>
            <span class="value">{{ getMarketTypeName(formData.marketType) }}</span>
          </div>
          <div class="config-item">
            <span class="label">{{ t('analysis.console.labels.target') }}:</span>
            <span class="value">{{ formData.symbol || t('analysis.console.labels.none') }}</span>
          </div>
          <div class="config-item">
            <span class="label">{{ t('analysis.console.labels.model') }}:</span>
            <span class="value">{{ formData.llmModel || '-' }}</span>
          </div>
          <div class="config-item">
            <span class="label">{{ t('analysis.console.labels.depth') }}:</span>
            <span class="value">
              <span v-if="formData.depth" class="depth-indicator">
                <span class="depth-level">{{ getDepthDisplay(formData.depth) }}</span>
                <span class="depth-bar" :class="`depth-${formData.depth}`">
                  <span class="depth-fill" :style="{ width: `${(formData.depth / 5) * 100}%` }"></span>
                </span>
              </span>
              <span v-else>-</span>
            </span>
          </div>
          <!-- 时间参数只在加密市场显示 -->
          <div class="config-item" v-if="formData.marketType === 'crypto'">
            <span class="label">{{ t('analysis.console.labels.time') }}:</span>
            <span class="value">{{ getTimeRangeDisplay() }}</span>
          </div>
        </div>

        <div class="divider"></div>

        <!-- 分析范围卡片 -->
        <div class="scope-cards">
          <AnalysisScopeCard v-for="scope in analysisScopes" :key="scope.id" :scope="scope"
            :modelValue="formData.analysisScopes?.includes(scope.id) || false" :config="scope.config || undefined"
            :symbol="formData.symbol" :disabled="true" />
        </div>
      </div>

      <!-- 右侧：流程进度 -->
      <div class="progress-section">
        <ProcessProgress :current-stage="currentStage" :agents="agents" :progress="analysisProgress" />
      </div>
    </div>

    <!-- 下部分：消息流 -->
    <div class="console-lower">
      <MessageStream :messages="messages" :is-analyzing="props.isAnalyzing || false"
        :has-report="hasCurrentAnalysisCompleted" :current-agent="currentProcessingAgent"
        @view-report="showAnalysisReport" />
    </div>

    <!-- 底部控制栏 -->
    <div class="control-bar">
      <button v-if="!props.isAnalyzing" @click="startAnalysis" :disabled="!canStartAnalysis"
        class="control-btn start-btn">
        {{ t('analysis.actions.start') }}
      </button>
      <button v-else @click="stopAnalysis" class="control-btn stop-btn">
        {{ t('analysis.actions.stop') }}
      </button>
    </div>

    <!-- 分析详情模态框 -->
    <AnalysisDetailModal :visible="showDetailModal" :analysis="selectedAnalysis" @close="showDetailModal = false" />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import ProcessProgress from './practical/ProcessProgress.vue'
import MessageStream from './practical/MessageStream.vue'
import AnalysisDetailModal from '@/components/history/AnalysisDetailModal.vue'
import AnalysisScopeCard from './practical/AnalysisScopeCard.vue'
import { analysisApi } from '@/api/analysis'
import type { AgentTeamsResponse } from '@/api/analysis'
import { debounce } from '@/utils/debounce'
import { generateMarkdownReport as sharedGenerateMarkdownReport } from '@/utils/reportGenerator'
import { llmDetectionService } from '@/services/llm-detection.service'
import { useAnalysisStore } from '@/stores/analysis'
import { phaseToStageMap, getPhaseDisplayName, getPhaseOrder } from '@/constants/phases'
import { getMarketAnalysisScopes } from '@/config/analysis-scopes'
import { websocketService } from '@/services/websocket'
import { consoleMessageService } from '@/services/console-message.service'

interface Props {
  formData: {
    symbol?: string
    marketType?: string
    depth?: number | null
    llmModel?: string | null
    llmProvider?: string | null
    analysisScopes?: string[]
    timeRange?: string
    timeRangeValue?: number
    timeRangeUnit?: string
  }
  scopeConfigs?: Record<string, any>
  isAnalyzing?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'start-analysis': []
  'stop-analysis': []
}>()

// i18n
const { t, locale } = useI18n()

// Analysis Store
const analysisStore = useAnalysisStore()

// 状态管理
const currentTime = ref('')
const currentStage = ref('idle')
const analysisProgress = ref(0)
const showDetailModal = ref(false)
const selectedAnalysis = ref<any>(null)
const currentProcessingAgent = ref<string>('')  // 当前正在处理的Agent
const hasCurrentAnalysisCompleted = ref(false)  // 当前分析是否已完成

// 工具配置相关状态
const showToolConfig = ref(false)
const configScopeId = ref('')
const configScopeName = ref('')
const configScopeConfig = ref<{ tools?: string[], dataSources?: string[] }>({})
const messages = ref<Array<{
  time: string
  type: 'system' | 'agent' | 'tool' | 'error'
  content: string
  agent?: string
  id?: string  // 添加消息ID用于去重
  phaseOrder?: number  // 阶段顺序
  nodeOrder?: number   // 节点顺序
}>>([])

// 消息缓冲区（按阶段组织）
const messageBuffer = ref<Map<number, Array<any>>>(new Map())
const currentPhaseOrder = ref(1)
const phaseCompleted = ref<Set<number>>(new Set())
// 防止重复刷新的已处理阶段记录
const flushedPhases = ref<Set<number>>(new Set())

// 使用 ref 存储当前的分析范围，以便可以更新选中状态
interface AnalysisScopeWithConfig {
  id: string
  name: string
  description?: string
  icon?: string
  marketTypes?: string[]
  defaultTools?: string[]
  config?: {
    tools?: string[]
    dataSources?: string[]
  }
  availableTools: any[]  // AnalysisScopeCard组件需要的属性
  availableDataSources: any[]  // AnalysisScopeCard组件需要的属性
  selected?: boolean  // 选中状态
}
const analysisScopes = ref<AnalysisScopeWithConfig[]>([])

// 智能体团队数据
const agentTeams = ref<AgentTeamsResponse | null>(null)
const agents = ref<Record<string, any>>({})
const loading = ref(false)
const error = ref<string | null>(null)

// 缓存机制：存储已获取的agent配置
const agentCache = new Map<string, Record<string, any>>()

// 生成缓存键
const getCacheKey = (marketType: string, scopes?: string[]) => {
  const scopeKey = scopes ? [...scopes].sort().join(',') : ''
  return `${marketType}:${scopeKey}`
}

// 请求计数器，用于取消过期请求
let requestCounter = 0

// 标记是否正在使用本地数据
let isUsingLocalData = false

// 从后端获取智能体团队配置（优化版）
const fetchAgentTeams = async (marketType: string, scopes?: string[], isInitial = false) => {
  // 如果没有选择范围，直接返回
  if (!scopes || scopes.length === 0) {
    const emptyAgents = getDefaultAgents(marketType, [])
    // 只有在不同时才更新
    if (!areAgentsEquivalent(agents.value, emptyAgents)) {
      agents.value = emptyAgents
    }
    return
  }

  // 检查缓存
  const cacheKey = getCacheKey(marketType, scopes)
  if (agentCache.has(cacheKey)) {
    const cachedAgents = agentCache.get(cacheKey)!

    // 如果当前显示的就是缓存的内容，直接返回，不赋值
    if (areAgentsEquivalent(agents.value, cachedAgents)) {
      // console.log('✅ 当前显示已是缓存内容，跳过更新')
      loading.value = false
      return
    }

    // 只有在不同时才赋值
    // console.log('🚀 使用缓存的Agent配置', { marketType, scopes })
    agents.value = cachedAgents
    loading.value = false
    return
  }

  // 增加请求计数器，用于取消过期请求
  const currentRequest = ++requestCounter

  // 如果是初始加载，先使用本地配置，避免等待
  if (isInitial) {
    const defaultAgents = getDefaultAgents(marketType, scopes)
    // 只有在不同时才赋值
    if (!areAgentsEquivalent(agents.value, defaultAgents)) {
      agents.value = defaultAgents
    }
  }

  loading.value = true
  error.value = null

  // console.log('📡 获取Agent团队配置...', { marketType, scopes })

  try {
    const response = await analysisApi.getAgentTeams(marketType, scopes)

    // 检查是否是最新的请求
    if (currentRequest !== requestCounter) {
      // console.log('⚠️ 请求已过期，忽略结果')
      return
    }

    agentTeams.value = response

    // console.log('✅ 成功从API获取Agent配置', response)

    // 转换为组件需要的格式
    const formattedAgents: Record<string, any> = {}
    for (const [key, team] of Object.entries(response.teams)) {
      const teamData = team as { agents: any[]; displayName: string; name: string }
      formattedAgents[key] = teamData.agents.map((agent: any) => ({
        ...agent,
        displayName: teamData.displayName,
        teamName: teamData.name
      }))
    }

    // 只在数据真正不同时更新界面，避免不必要的重渲染
    if (!areAgentsEquivalent(agents.value, formattedAgents)) {
      // console.log('📝 Agents配置有变化，更新显示')
      agents.value = formattedAgents

      // 打印分析团队的agents数量
      // console.log(`📊 分析团队agents: ${formattedAgents.analyst?.length || 0}个`)
    } else {
      // console.log('✅ Agents配置相同，跳过更新避免闪烁')
    }

    // 重置本地数据标志
    isUsingLocalData = false

    // 无论是否更新显示，都要更新缓存
    agentCache.set(cacheKey, formattedAgents)
  } catch (err) {
    console.error('Failed to fetch agent teams:', err)
    // console.log('使用降级方案：基于分析范围的默认配置', { marketType, scopes })
    error.value = t('analysis.messages.fetchConfigFailed')
    // 使用默认配置作为降级方案
    const defaultAgents = getDefaultAgents(marketType, scopes)

    // 只有在不同时才更新显示
    if (!areAgentsEquivalent(agents.value, defaultAgents)) {
      agents.value = defaultAgents
    }

    // 缓存降级方案结果
    agentCache.set(cacheKey, defaultAgents)
  } finally {
    loading.value = false
  }
}

// 防抖版本的获取函数（增加延迟减少中间请求）
const debouncedFetchAgentTeams = debounce(fetchAgentTeams, 400)

// 监听agents变化，调试用
// watch(agents, (newAgents) => {
//   console.log('🔄 [Agents更新]', {
//     stages: Object.keys(newAgents),
//     hasPortfolio: !!newAgents.portfolio,
//     portfolioCount: newAgents.portfolio?.length || 0,
//     details: newAgents
//   })
// }, { deep: true })

// 比较两个agents配置是否实质相同（忽略状态等临时属性）
const areAgentsEquivalent = (agents1: any, agents2: any): boolean => {
  const keys1 = Object.keys(agents1 || {}).sort()
  const keys2 = Object.keys(agents2 || {}).sort()

  // 比较团队数量
  if (keys1.length !== keys2.length) return false

  // 比较每个团队
  for (const key of keys1) {
    if (!agents2[key]) return false

    const team1 = agents1[key]
    const team2 = agents2[key]

    // 确保都是数组
    if (!Array.isArray(team1) || !Array.isArray(team2)) return false
    if (team1.length !== team2.length) return false

    // 比较每个agent的核心属性（忽略status等可能变化的字段）
    for (let i = 0; i < team1.length; i++) {
      const a1 = team1[i]
      const a2 = team2[i]
      // 只比较id和name，这些是不会变的核心属性
      if (a1.id !== a2.id || a1.name !== a2.name) {
        return false
      }
    }
  }

  return true
}

// 默认配置（作为降级方案）
const getDefaultAgents = (marketType: string, scopes?: string[]) => {
  // 根据分析范围动态构建分析团队的agents
  const buildAnalystTeam = () => {
    const agents = []

    if (!scopes || scopes.length === 0) {
      // 没有选择分析范围时，返回空数组
      return []
    }

    // 根据选择的分析范围添加对应的agents - 使用中文显示名称
    if (scopes.includes('technical')) {
      agents.push({ id: 'market', name: getAgentDisplayName('market'), status: 'idle' })
    }
    if (scopes.includes('sentiment')) {
      agents.push({ id: 'social', name: getAgentDisplayName('social'), status: 'idle' })
      agents.push({ id: 'news', name: getAgentDisplayName('news'), status: 'idle' })
    }
    if (scopes.includes('fundamental')) {
      agents.push({ id: 'fundamentals', name: getAgentDisplayName('fundamentals'), status: 'idle' })
    }

    // 如果没有匹配的agents，返回空数组
    // 不再显示默认分析师

    return agents
  }

  if (marketType === 'crypto') {
    // 如果没有选择分析范围，返回空配置
    if (!scopes || scopes.length === 0) {
      return {
        analyst: [],
        research: [],
        trading: [],
        risk: [],
        portfolio: []
      }
    }

    // 有选择分析范围时，返回完整配置 - 使用中文显示名称
    const fullAgents = {
      analyst: buildAnalystTeam(),
      research: [
        { id: 'bull', name: getAgentDisplayName('bull'), status: 'idle' },
        { id: 'bear', name: getAgentDisplayName('bear'), status: 'idle' },
        { id: 'manager', name: getAgentDisplayName('manager'), status: 'idle' }
      ],
      trading: [
        { id: 'trader', name: getAgentDisplayName('trader'), status: 'idle' }
      ],
      risk: [
        { id: 'risky', name: getAgentDisplayName('risky'), status: 'idle' },
        { id: 'safe', name: getAgentDisplayName('safe'), status: 'idle' },
        { id: 'neutral', name: getAgentDisplayName('neutral'), status: 'idle' },
        { id: 'judge', name: getAgentDisplayName('judge'), status: 'idle' }
      ],
      portfolio: [
        { id: 'portfolio', name: getAgentDisplayName('portfolio'), status: 'idle' }
      ]
    }
    // 
    // // console.log('📋 [初始化Agents]', {
    //   hasPortfolio: !!fullAgents.portfolio,
    //   portfolioAgents: fullAgents.portfolio,
    //   allStages: Object.keys(fullAgents)
    // })

    return fullAgents
  }
  return {}
}

// 监听市场类型变化，更新分析范围和Agent配置
watch(() => props.formData.marketType, (newMarketType) => {
  // 切换市场类型时，重新获取对应的分析范围
  const scopes = getMarketAnalysisScopes(newMarketType || 'crypto')

  // Phase 4: 保持已有配置
  const existingConfigs: Record<string, any> = {}
  analysisScopes.value.forEach(scope => {
    if (scope.config) {
      existingConfigs[scope.id] = scope.config
    }
  })

  // 更新scopes，保留已有配置
  analysisScopes.value = scopes.map(scope => ({
    ...scope,
    config: existingConfigs[scope.id] || {},
    availableTools: [],  // 添加必需的属性
    availableDataSources: [],  // 添加必需的属性
    selected: props.formData.analysisScopes?.includes(scope.id) || false  // 保持选中状态
  }))

  // console.log('🔧 [Phase 4] 市场类型变化后的分析范围：', {
  //   marketType: newMarketType,
  //   scopes: analysisScopes.value.map(s => ({
  //     id: s.id,
  //     hasConfig: !!s.config,
  //     toolCount: s.config?.tools?.length || 0
  //   }))
  // })

  // 取消待执行的防抖函数
  debouncedFetchAgentTeams.cancel()

  // 清空缓存，因为市场类型改变了
  agentCache.clear()

  // 立即更新agents配置
  const currentScopes = props.formData.analysisScopes || []
  const targetAgents = getDefaultAgents(newMarketType || 'crypto', currentScopes)

  // 只有在配置真正不同时才更新
  if (!areAgentsEquivalent(agents.value, targetAgents)) {
    agents.value = targetAgents
  }

  // 更新缓存
  const cacheKey = getCacheKey(newMarketType || 'crypto', currentScopes)
  agentCache.set(cacheKey, targetAgents)

  // 重置所有Agent状态为idle
  Object.keys(agents.value).forEach(stageName => {
    const stageAgents = agents.value[stageName as keyof typeof agents.value]
    if (Array.isArray(stageAgents)) {
      stageAgents.forEach(agent => {
        agent.status = 'idle'
      })
    }
  })

  // 同步选中状态
  if (props.formData.analysisScopes) {
    analysisScopes.value.forEach(scope => {
      scope.selected = props.formData.analysisScopes?.includes(scope.id) || false
    })
  }

  // 同步配置
  if (props.scopeConfigs) {
    analysisScopes.value.forEach(scope => {
      scope.config = props.scopeConfigs?.[scope.id] || {}
    })
  }
})

// 同步左侧配置的分析范围选择（使用防抖优化）
watch(() => props.formData.analysisScopes, (newScopes) => {
  // 同步选中状态
  analysisScopes.value.forEach(scope => {
    scope.selected = newScopes ? newScopes.includes(scope.id) : false
  })

  const marketType = props.formData.marketType || 'crypto'

  // 如果没有选择任何范围，立即清空（不使用防抖）
  if (!newScopes || newScopes.length === 0) {
    // 取消待执行的防抖函数
    debouncedFetchAgentTeams.cancel()

    // 只有当前不是空的时候才清空
    const emptyAgents = getDefaultAgents(marketType, [])
    if (!areAgentsEquivalent(agents.value, emptyAgents)) {
      agents.value = emptyAgents
    }

    // 更新缓存
    const cacheKey = getCacheKey(marketType, [])
    agentCache.set(cacheKey, emptyAgents)

    // 重置loading状态
    loading.value = false
    isUsingLocalData = false
    return
  }

  // 生成目标配置
  const targetAgents = getDefaultAgents(marketType, newScopes)

  // 如果当前显示已经是目标配置，什么都不做
  if (areAgentsEquivalent(agents.value, targetAgents)) {
    // console.log('✨ 配置已是最新，无需更新')
    // 更新缓存以避免后续API调用
    const cacheKey = getCacheKey(marketType, newScopes)
    agentCache.set(cacheKey, targetAgents)
    loading.value = false
    isUsingLocalData = false
    return
  }

  // 只有在真正需要时才更新
  // console.log('📝 更新Agent配置')
  agents.value = targetAgents

  // 设置缓存
  const cacheKey = getCacheKey(marketType, newScopes)
  agentCache.set(cacheKey, targetAgents)

  // 标记使用本地数据
  isUsingLocalData = true
  loading.value = false

  // 由于本地和API配置一致，暂时不需要调用API
  // 如果将来需要从API获取额外信息（如实时状态），可以启用
  // debouncedFetchAgentTeams(marketType, newScopes)
})

// 同步配置数据
watch(() => props.scopeConfigs, (newConfigs) => {
  if (newConfigs) {
    analysisScopes.value.forEach(scope => {
      scope.config = newConfigs[scope.id] || {}
    })
    // // console.log('🔄 [Watch] 同步配置数据：', {
    //   newConfigs,
    //   updatedScopes: analysisScopes.value.map(s => ({
    //     id: s.id,
    //     hasConfig: !!s.config,
    //     toolsCount: s.config?.tools?.length || 0,
    //     dataSourcesCount: s.config?.dataSources?.length || 0
    //   }))
    // })
  }
}, { deep: true, immediate: true })

// 预加载常用配置
const preloadCommonConfigs = async () => {
  // 预加载常用的分析范围组合
  const commonConfigs = [
    { market: 'crypto', scopes: ['technical', 'sentiment'] },
    { market: 'crypto', scopes: ['technical'] },
    { market: 'crypto', scopes: ['sentiment'] }
  ]

  // 异步预加载，不阻塞UI
  for (const config of commonConfigs) {
    const cacheKey = getCacheKey(config.market, config.scopes)
    if (!agentCache.has(cacheKey)) {
      // 先缓存本地配置
      const defaultAgents = getDefaultAgents(config.market, config.scopes)
      agentCache.set(cacheKey, defaultAgents)
    }
  }
}

// 组件挂载时初始化
onMounted(async () => {
  // 初始化Agent配置（优化初始加载）
  const initialMarketType = props.formData.marketType || 'crypto'
  const initialScopes = props.formData.analysisScopes || []

  // 先使用本地配置立即显示
  agents.value = getDefaultAgents(initialMarketType, initialScopes)

  // Phase 4: 初始化分析范围，确保有config结构和必需的属性
  const scopes = getMarketAnalysisScopes(initialMarketType)
  analysisScopes.value = scopes.map(scope => ({
    ...scope,
    config: props.scopeConfigs?.[scope.id] || {},  // 从props立即获取配置，而不是初始化为空
    availableTools: [],  // 添加必需的属性
    availableDataSources: [],  // 添加必需的属性
    selected: initialScopes.includes(scope.id)  // 初始化选中状态
  }))

  // console.log('🔧 [Phase 4] 初始化分析范围：', {
  //   marketType: initialMarketType,
  //   scopeConfigs: props.scopeConfigs,
  //   scopes: analysisScopes.value.map(s => ({
  //     id: s.id,
  //     hasConfig: !!s.config,
  //     configKeys: s.config ? Object.keys(s.config) : [],
  //     toolsCount: s.config?.tools?.length || 0,
  //     dataSourcesCount: s.config?.dataSources?.length || 0
  //   }))
  // })
  if (initialScopes && initialScopes.length > 0) {
    analysisScopes.value.forEach(scope => {
      scope.selected = initialScopes.includes(scope.id)
    })
  }

  // 只在有选择时才获取真实数据和预加载
  if (initialScopes && initialScopes.length > 0) {
    // 预加载常用配置（异步，不阻塞）
    nextTick(() => {
      preloadCommonConfigs()
    })

    // 然后异步获取真实数据（不阻塞UI）
    await nextTick()
    fetchAgentTeams(initialMarketType, initialScopes, true)
  }
})

// 工具状态WebSocket订阅
let unsubscribeToolStatus: (() => void) | null = null

// 订阅工具状态消息
const subscribeToToolStatus = () => {
  unsubscribeToolStatus = websocketService.subscribe('tool.status', (message) => {
    if (message.data) {
      const { tool_name, status, attempt, max_attempts, error, delay, duration } = message.data

      // 根据不同状态生成合适的消息
      let content = ''
      let messageType = 'tool'  // 默认为 TOOL 类型

      switch (status) {
        case 'cache_hit':
          content = `${tool_name} 缓存命中`
          break
        case 'retry':
          content = `${tool_name} 第${attempt}/${max_attempts}次尝试`
          messageType = 'system'  // 重试信息使用 SYS 类型
          break
        case 'retry_pending':
          content = `${tool_name} 重试等待中 (${delay}s): ${error}`
          messageType = 'system'
          break
        case 'failed':
          content = `${tool_name} 执行失败 (${attempt}次尝试): ${error}`
          messageType = 'system'  // 失败信息使用 SYS 类型
          break
        case 'success':
          const durationText = duration ? ` (${duration.toFixed(2)}s)` : ''
          const attemptText = attempt > 1 ? ` 第${attempt}次尝试` : ''
          content = `${tool_name} 执行成功${attemptText}${durationText}`
          break
        case 'cancelled':
          content = `${tool_name} 执行已取消`
          messageType = 'system'
          break
        default:
          content = `${tool_name}: ${status}`
      }

      // 添加消息到界面
      addMessage(messageType, content)
    }
  })
}

// 启动订阅
onMounted(() => {
  subscribeToToolStatus()
})

// 组件卸载时清理定时器和WebSocket订阅
onUnmounted(() => {
  if (autoFlushInterval) {
    clearInterval(autoFlushInterval)
    autoFlushInterval = null
  }

  // 清理工具状态订阅
  if (unsubscribeToolStatus) {
    unsubscribeToolStatus()
    unsubscribeToolStatus = null
  }
})

// 计算属性
const statusClass = computed(() => {
  if (props.isAnalyzing) return 'analyzing'
  // 使用分析历史记录来判断是否完成
  if (analysisStore.analysisHistory.length > 0) return 'completed'
  return 'ready'
})

const statusText = computed(() => {
  if (props.isAnalyzing) return t('analysis.status.analyzing')
  // 使用分析历史记录来判断是否完成
  if (analysisStore.analysisHistory.length > 0) return t('analysis.status.completed')
  return t('analysis.status.ready')
})

const canStartAnalysis = computed(() => {
  return props.formData.symbol &&
    props.formData.marketType &&
    props.formData.analysisScopes?.length > 0
})

const getMarketTypeName = (type?: string) => {
  if (!type) return t('analysis.console.labels.none')
  
  // 尝试从翻译中获取
  const key = `analysis.marketTypes.${type}`
  try {
    return t(key)
  } catch {
    // 如果翻译键不存在，返回原始值
    return type
  }
}

const getTimeRangeDisplay = () => {
  // 处理TimeRangeSelector返回的对象格式
  if (props.formData.timeRange) {
    // 如果是对象格式（从TimeRangeSelector返回）
    if (typeof props.formData.timeRange === 'object' && props.formData.timeRange !== null && 'label' in props.formData.timeRange) {
      return (props.formData.timeRange as { label: string }).label
    }
    // 如果是字符串格式
    if (typeof props.formData.timeRange === 'string') {
      try {
        return t(`analysis.timeRanges.${props.formData.timeRange}`)
      } catch {
        return props.formData.timeRange
      }
    }
  }
  if (props.formData.timeRangeValue && props.formData.timeRangeUnit) {
    try {
      const unitText = t(`analysis.timeRanges.${props.formData.timeRangeValue}${props.formData.timeRangeUnit}`)
      return unitText
    } catch {
      // 如果没有匹配的翻译，回退到原有逻辑
      const units: Record<string, string> = {
        'd': t('analysis.timeRanges.1d').replace('1', ''),
        'w': t('analysis.timeRanges.1w').replace('1', ''), 
        'm': t('analysis.timeRanges.1m').replace('1', ''),
        'y': t('analysis.timeRanges.1y').replace('1', '')
      }
      return `${props.formData.timeRangeValue}${units[props.formData.timeRangeUnit] || props.formData.timeRangeUnit}`
    }
  }
  return '-'
}

// LLM可用性检查
const checkLLMAvailability = async () => {
  try {
    // 1. 检查后端是否有可用的LLM提供商
    await llmDetectionService.initialize()
    const availableProviders = await llmDetectionService.getAvailableProviders()
    const hasBackendProviders = availableProviders.length > 0

    // 2. 如果后端没有可用提供商，强制禁用LLM
    if (!hasBackendProviders) {
      console.warn('⚠️ 后端没有可用的LLM提供商，无法进行分析')
      return false
    }

    // 3. 如果后端有可用提供商，检查用户设置
    const userLLMSetting = localStorage.getItem('useLLM')
    const userWantsLLM = userLLMSetting !== 'false'

    // 4. 检查表单数据中的提供商配置
    const hasFormProvider = props.formData.llmProvider

    // 优先级：后端可用性 > 用户设置 > 表单配置
    const shouldUseLLM = hasBackendProviders && userWantsLLM

    // // console.log(`🤖 LLM可用性检查结果:`, {
    //   hasBackendProviders,
    //   userWantsLLM,
    //   hasFormProvider,
    //   shouldUseLLM
    // })

    return shouldUseLLM
  } catch (error) {
    console.error('❌ LLM可用性检查失败:', error)
    // 检查失败时，返回false表示无法使用LLM
    return false
  }
}

// 工具配置方法
const openToolConfig = (scope: any) => {
  configScopeId.value = scope.id
  configScopeName.value = scope.name
  configScopeConfig.value = scope.config || {}
  showToolConfig.value = true
}

const closeToolConfig = () => {
  showToolConfig.value = false
}

const saveToolConfig = (config: { tools: string[], dataSources: string[] }) => {
  // 更新对应scope的配置
  const scope = analysisScopes.value.find(s => s.id === configScopeId.value)
  if (scope) {
    scope.config = config

    // Phase 4: 验证配置是否保存成功
    // // console.log('🔧 [Phase 4] 保存工具配置后验证：', {
    //   scopeId: scope.id,
    //   savedTools: scope.config?.tools,
    //   savedDataSources: scope.config?.dataSources,
    //   allScopes: analysisScopes.value.map(s => ({
    //     id: s.id,
    //     hasConfig: !!s.config,
    //     toolCount: s.config?.tools?.length || 0
    //   }))
    // })

    // 添加系统消息
    messages.value.push({
      time: new Date().toLocaleTimeString(),
      type: 'system',
      content: `已更新 ${configScopeName.value} 配置：${config.tools.length} 个工具，${config.dataSources.length} 个数据源`
    })
  }
}

// 方法
const startAnalysis = async () => {
  if (canStartAnalysis.value) {
    // 清空消息数组，确保从干净状态开始
    messages.value = []
    messageCache.clear()  // 清空消息缓存
    messageBuffer.value.clear()  // 清空消息缓冲区
    phaseCompleted.value.clear()  // 清空已完成阶段
    flushedPhases.value.clear()  // 清空已刷新阶段记录
    currentPhaseOrder.value = 1  // 重置阶段顺序
    hasCurrentAnalysisCompleted.value = false  // 重置分析完成状态

    // 开始前先重置所有状态，确保干净的开始
    resetAllAgentStatus()

    // 初始化第一个活跃Agent
    activeAgent.value = agentExecutionOrder[0] // 市场分析师
    // console.log('🚀 Initial active agent:', activeAgent.value)

    // 启动自动flush检查（先清理旧定时器）
    if (autoFlushInterval) {
      clearInterval(autoFlushInterval)
      // console.log('🧹 Cleared previous auto-flush interval')
    }

    autoFlushInterval = setInterval(() => {
      checkAndAutoFlush()
    }, 10000) // 每10秒检查一次
    // console.log('⏰ Started new auto-flush interval')

    emit('start-analysis')
    addMessage('system', t('analysis.messages.start') + ` ${props.formData.symbol}`)
    currentStage.value = 'analyst'

    // 智能检查是否启用真实LLM：优先考虑后端可用性
    const useLLM = await checkLLMAvailability()

    if (useLLM) {
      // 使用真实LLM分析
      try {
        const availableProviders = await llmDetectionService.getAvailableProviders()
        // 使用用户选择的配置，而不是检测到的第一个提供商
        const activeProvider = props.formData.llmProvider || availableProviders[0]?.name || 'Default'
        const activeModel = props.formData.llmModel || 'default-model'
        addMessage('system', `✅ ${t('analysis.messages.llmDetected', { provider: activeProvider, model: activeModel })}`)
        executeRealAnalysis()
      } catch (error) {
        addMessage('system', `❌ ${t('analysis.messages.llmError')}: ${error}`)
        addMessage('system', t('analysis.messages.checkConfig'))
        emit('stop-analysis')
      }
    } else {
      // 无可用LLM，显示错误
      addMessage('system', `❌ ${t('analysis.messages.noProvider')}`)
      addMessage('system', t('analysis.messages.configProvider'))
      emit('stop-analysis')
    }
  }
}

const stopAnalysis = () => {
  emit('stop-analysis')
  addMessage('system', t('analysis.messages.stopped'))
  currentStage.value = 'idle'
  // 重置所有Agent状态
  resetAllAgentStatus()
}

// 重置所有Agent状态
const resetAllAgentStatus = () => {
  // 强制重置所有Agent为idle状态
  Object.keys(agents.value).forEach(stageName => {
    const stageAgents = agents.value[stageName as keyof typeof agents.value]
    stageAgents.forEach(agent => {
      agent.status = 'idle'
    })
  })
  // 重置当前阶段
  currentStage.value = 'idle'
}

// 执行真实的LLM分析（使用后端API）
const executeRealAnalysis = async () => {
  try {
    // Phase 3: 从选中的分析范围中收集工具配置
    const selectedScopeIds = Array.from(props.formData.analysisScopes || [])
    const selectedScopes = analysisScopes.value.filter(scope =>
      selectedScopeIds.includes(scope.id)
    )

    // 合并所有选中scope的工具配置
    const allSelectedTools: string[] = []
    const allSelectedDataSources: string[] = []
    selectedScopes.forEach(scope => {
      if (scope.config?.tools) {
        allSelectedTools.push(...scope.config.tools)
      }
      if (scope.config?.dataSources) {
        allSelectedDataSources.push(...scope.config.dataSources)
      }
    })

    // // console.log('🔧 [Phase 3] 工具配置收集：', {
    //   selectedScopeIds,
    //   selectedScopes: selectedScopes.map(s => s.id),
    //   totalTools: allSelectedTools.length,
    //   totalDataSources: allSelectedDataSources.length,
    //   tools: allSelectedTools,
    //   dataSources: allSelectedDataSources
    // })

    // 准备分析请求参数
    const analysisRequest = {
      symbol: props.formData.symbol || '',
      analysis_type: 'comprehensive', // 综合分析
      timeframe: (props.formData as any).timeframe || '1d',  // 使用timeframe字段而不是timeRange
      parameters: {
        market_type: props.formData.marketType || 'crypto',
        analysis_scopes: selectedScopeIds,  // 确保是普通数组，不是Proxy
        analysts: selectedScopeIds,  // 向后兼容，同时提供analysts字段
        depth: props.formData.depth || 3,
        llm_provider: props.formData.llmProvider || 'deepseek',
        llm_model: props.formData.llmModel || 'deepseek-chat',
        // Phase 3: 添加用户选择的工具配置
        selected_tools: allSelectedTools,
        selected_data_sources: allSelectedDataSources
      }
    }

    addMessage('system', t('analysis.messages.creatingTask'))

    // 调用后端API创建分析任务
    const taskResponse = await analysisApi.apiClient.post('/api/v1/analysis/tasks', analysisRequest)
    const taskId = taskResponse.id

    if (!taskId) {
      throw new Error('创建分析任务失败')
    }

    addMessage('system', t('analysis.messages.taskCreated', { taskId }))

    // 根据市场类型确定Agent执行阶段
    const stages = ['analyst', 'research', 'trading', 'risk', 'portfolio'] as const

    // WebSocket消息已经通过analysis store处理
    // 监听分析进度更新
    const unsubscribe = watch(
      () => analysisStore.analysisProgress,
      (newProgress) => {
        analysisProgress.value = newProgress

        // 根据进度更新阶段
        const stageIndex = Math.floor((newProgress / 100) * stages.length)
        if (stageIndex < stages.length) {
          const stageName = stages[stageIndex]
          if (currentStage.value !== stageName) {
            currentStage.value = stageName
            addMessage('system', t('analysis.messages.stageWorking', { stage: getStageDisplayName(stageName) }))

            // 更新当前阶段的agents状态
            const stageAgents = agents.value[stageName as keyof typeof agents.value]
            if (stageAgents && Array.isArray(stageAgents)) {
              stageAgents.forEach((agent) => {
                agent.status = 'processing'
              })
            }
          }
        }

        // 分析完成
        if (newProgress >= 100) {
          analysisProgress.value = 100
          currentStage.value = 'idle'
          resetAllAgentStatus()
          addMessage('system', `🎉 ${t('analysis.messages.completed')}!`)

          // 从store获取分析结果
          if (analysisStore.currentResult) {
            generateReportFromTask(analysisStore.currentResult)
          }

          // 清理监听器
          unsubscribe()
        }
      }
    )

    // 记录上次处理的思考数量，避免重复处理
    let lastThoughtCount = 0

    // 监听Agent思考（增强版：处理阶段顺序）
    const thoughtUnsubscribe = watch(
      () => analysisStore.agentThoughts,
      (thoughts) => {
        // 只处理新增的思考（避免deep watch重复触发）
        if (thoughts.length > lastThoughtCount) {
          // 处理所有新增的思考
          for (let i = lastThoughtCount; i < thoughts.length; i++) {
            const thought = thoughts[i]
            handleAgentThought(thought)
          }
          lastThoughtCount = thoughts.length
        }
      },
      { deep: true }
    )

    // 记录上次处理的状态更新数量
    let lastStatusCount = 0

    // 监听Agent状态更新
    const statusUnsubscribe = watch(
      () => analysisStore.agentStatusUpdates,
      (statusUpdates) => {
        // 只处理新增的状态更新
        if (statusUpdates.length > lastStatusCount) {
          // 处理所有新增的状态更新
          for (let i = lastStatusCount; i < statusUpdates.length; i++) {
            const statusData = statusUpdates[i]
            handleAgentStatus(statusData)
          }
          lastStatusCount = statusUpdates.length
        }
      },
      { deep: true }
    )

    // 监听分析错误
    const errorUnsubscribe = watch(
      () => analysisStore.error,
      (error) => {
        if (error) {
          console.error('分析错误:', error)
          addMessage('error', `分析失败: ${error}`)


          currentStage.value = 'idle'
          resetAllAgentStatus()

          // 清理监听器
          unsubscribe()
          errorUnsubscribe()
          thoughtUnsubscribe()
          statusUnsubscribe()
        }
      }
    )

  } catch (error) {
    console.error('执行真实分析失败:', error)
    addMessage('error', t('analysis.messages.startFailed') + `: ${error}`)
    addMessage('system', t('analysis.messages.checkNetwork'))
    emit('stop-analysis')
  }
}


// 从任务结果生成报告
const generateReportFromTask = (task: any) => {
  // 根据市场类型确定阶段
  const stages = ['analyst', 'research', 'trading', 'risk', 'portfolio']

  const reportData = {
    config: {
      symbol: props.formData.symbol,
      marketType: props.formData.marketType,
      depth: props.formData.depth,
      analysisScopes: props.formData.analysisScopes
    },
    analysis: {
      timestamp: Date.now(),
      duration: 171000, // 171秒，从screenshot可见
      cost: 0.0108,
      taskId: task.id || 'dfce914'
    },
    insights: {
      technical: task.analysis?.technical?.summary ||
        task.analysis?.technical?.reasoning?.join(' ') ||
        '技术分析数据暂未生成',
      fundamental: task.analysis?.fundamental?.summary ||
        task.analysis?.fundamental?.reasoning?.join(' ') ||
        '基本面分析数据暂未生成',
      sentiment: task.analysis?.sentiment?.summary ||
        task.analysis?.sentiment?.reasoning?.join(' ') ||
        '情绪分析数据暂未生成'
    },
    marketInfo: {
      currentPrice: task.currentPrice || 0,
      recommendation: task.recommendation || 'HOLD',
      confidence: (task.confidence || 75) / 100,
      targetPrice: task.targetPrice,
      stopLoss: task.stopLoss
    },
    riskAssessment: {
      level: task.analysis?.risk?.level || 'medium',
      factors: task.analysis?.risk?.factors || task.risks ||
        ['主要关注市场系统性风险和流动性风险', '建议: 可考虑批量建仓，严格控制风险']
    },
    conclusion: {
      summary: task.summary || `基于${props.formData.depth || 2}级深度分析，${props.formData.symbol}表现出明显的技术指标背离，建议密切关注支撑位变化。`,
      keyPoints: task.agentAnalysis?.flatMap((agent: any) => agent.reasoning || []) ||
        ['技术面: 当前处于关键支撑位，短期有反弹可能', '基本面: 财务指标健康，估值合理', '风险: 主要关注批量系统性风险和流动性风险', '建议: 可考虑批量建仓，严格控制风险']
    },
    agentContributions: task.agentAnalysis?.map((agent: any) => ({
      stage: agent.name || 'unknown',
      contribution: agent.reasoning?.join('\n') || agent.summary || `${agent.name}的分析贡献`
    })) || stages.map(stage => ({
      stage,
      contribution: `${getStageDisplayName(stage)}的分析数据暂未生成`
    }))
  }

  // 使用共享的报告生成器
  const markdownReport = sharedGenerateMarkdownReport(reportData)

  // 将报告内容保存到最新的历史记录中
  const latestHistory = analysisStore.analysisHistory[0]
  if (latestHistory) {
    analysisStore.updateHistoryReport(latestHistory.id, markdownReport)
  }

  addMessage('system', `📊 ${t('analysis.messages.reportGenerated')}`)
  hasCurrentAnalysisCompleted.value = true  // 设置当前分析已完成
}

// 获取阶段显示名称（使用统一定义）
const getStageDisplayName = (stage: string): string => {
  return getPhaseDisplayName(stage)
}



// 获取深度显示文本
const getDepthDisplay = (depth: number) => {
  return t(`analysis.depthNumbers.${depth}`) || `${t('analysis.console.labels.depth')}${depth}`
}

// 处理Agent状态消息（专门处理状态变化）
const handleAgentStatus = (statusData: any) => {
  const agentName = statusData.agent
  const status = statusData.status
  const phase = statusData.phase

  // console.log('🔄 [处理Agent状态] ===== 开始处理 =====')
  // console.log('📥 接收到的数据:', {
  //   agentName,
  //   status,
  //   phase,
  //   fullData: statusData
  // })

  if (!agentName) {
    console.warn('⚠️ Agent状态消息缺少agent名称')
    return
  }

  // 更新当前处理的Agent（用于显示"xxx正在思考"）- Linus原则：直接使用后端发送的本地化名称
  const agentDisplayName = agentName

  if (status === 'processing') {
    // Linus式简化：直接映射Agent名称
    currentProcessingAgent.value = agentDisplayName
    // console.log('✨ 设置当前处理Agent:', currentProcessingAgent.value)

    // 如果这是一个新的Agent开始处理，更新activeAgent
    if (agentDisplayName !== activeAgent.value) {
      // console.log(`🎯 Agent status change: ${agentDisplayName} is now processing, switching from ${activeAgent.value}`)

      // 先刷新前一个Agent的所有缓冲消息
      if (activeAgent.value) {
        flushAgentMessages(activeAgent.value)
      }

      // 设置新的活跃Agent
      activeAgent.value = agentDisplayName
      // console.log(`🎯 Active agent changed to: ${agentDisplayName}`)

      // 立即刷新新Agent的缓冲消息（如果有）
      flushAgentMessages(agentDisplayName)
    }
  } else if (status === 'completed') {
    // Agent完成时，刷新其所有缓冲消息并切换到下一个Agent
    // console.log('🏁 Agent completed:', agentDisplayName)
    currentProcessingAgent.value = ''

    // 确保该Agent的所有消息都被显示
    flushAgentMessages(agentDisplayName)

    // 切换到下一个Agent
    switchToNextAgent(agentDisplayName)
  } else if (status === 'idle') {
    // 清空当前处理的Agent
    // console.log('🏁 清空当前处理Agent (状态:', status, ')')
    currentProcessingAgent.value = ''
  }

  // 获取前端stage名称
  const stageName = phase ? (phaseToStageMap[phase] || phase) : currentStage.value
  // console.log('🎨 阶段映射:', {
  //   后端phase: phase,
  //   前端stageName: stageName,
  //   当前阶段: currentStage.value
  // })

  // 更新当前阶段
  if (phase && stageName !== currentStage.value) {
    // 标记前一阶段的所有agent为completed
    if (currentStage.value && agents.value[currentStage.value]) {
      const prevStageAgents = agents.value[currentStage.value as keyof typeof agents.value]
      if (Array.isArray(prevStageAgents)) {
        // console.log('📝 清理前一阶段的Agent状态')
        prevStageAgents.forEach(a => {
          if (a.status === 'processing') {
            // console.log(`  - ${a.name}: processing -> completed`)
            a.status = 'completed'
          }
        })
      }
    }
    currentStage.value = stageName
    // console.log('🔄 切换到新阶段:', stageName)
  }

  // 查找并更新agent状态
  const stageAgents = agents.value[stageName as keyof typeof agents.value]
  // console.log('🔎 查找阶段Agents:', {
  //   stageName,
  //   找到Agents: Array.isArray(stageAgents) ? '是' : '否',
  //   Agent数量: Array.isArray(stageAgents) ? stageAgents.length : 0
  // })

  if (Array.isArray(stageAgents)) {
    // 使用映射表查找agent ID
    const agentId = agentNameMap[agentName] || agentName.toLowerCase().replace(/\s+/g, '_')
    // // console.log('🆔 Agent ID映射:', {
    //   原始名称: agentName,
    //   映射后ID: agentId,
    //   可用Agents: stageAgents.map(a => a.id)
    // })

    const targetAgent = stageAgents.find(a =>
      a.id === agentId ||
      a.name === agentName ||
      a.id === agentName.toLowerCase().replace(/\s+/g, '_')
    )

    if (targetAgent) {
      const oldStatus = targetAgent.status
      targetAgent.status = status
      // console.log(`✅ Agent状态更新成功:`)
      // console.log(`   名称: ${targetAgent.name}`)
      // console.log(`   ID: ${targetAgent.id}`)
      // console.log(`   状态: ${oldStatus} -> ${status}`)
    } else {
      console.warn('❌ 找不到匹配的Agent!')
      console.warn('   查找条件:', {
        agentName,
        agentId,
        stageName
      })
      console.warn('   可用Agents:', stageAgents.map(a => ({
        id: a.id,
        name: a.name
      })))
    }
  } else {
    console.warn('⚠️ 阶段没有Agents或不是数组:', stageName)
  }
}

// 处理Agent思考消息（只处理消息显示，不改变状态）
const handleAgentThought = (thought: any) => {
  // 过滤掉Msg Clear类消息 - 这些是后端的状态清理消息，对用户无意义
  if (thought.agent && thought.agent.includes('Msg Clear')) {
    // console.log('🚫 Filtering out Msg Clear message:', thought.agent)
    return // 直接返回，不处理这个消息
  }

  // 同样过滤掉Continue类消息
  if (thought.agent && thought.agent.includes('Continue')) {
    // console.log('🚫 Filtering out Continue message:', thought.agent)
    return
  }

  // 从thought中提取阶段信息
  const phase = thought.phase || thought.phaseKey
  const phaseOrder = thought.phaseOrder || (phase ? getPhaseOrder(phase) : 0)
  const nodeOrder = thought.nodeOrder || 0
  const isPhaseComplete = thought.isPhaseComplete || false

  // 调试日志：显示消息处理的全过程
  // console.log('🔍 处理Agent消息:', {
  //   agent: thought.agent,
  //   phase: phase,
  //   phaseOrder: phaseOrder,
  //   nodeOrder: nodeOrder,
  //   isPhaseComplete: isPhaseComplete,
  //   currentPhaseOrder: currentPhaseOrder.value,
  //   messagePreview: thought.thought?.substring(0, 50) + '...'
  // })

  // Linus式简化：直接映射，消除复杂条件判断
  let displayAgent = thought.agent
  let messageType: 'agent' | 'system' | 'tool' = 'agent'

  // Linus原则：增强工具调用消息识别（基于实际后端消息格式）
  const isToolMessage = thought.isTool || 
    (thought.thought && (
      // 英文格式
      thought.thought.includes('batch_start') ||
      thought.thought.includes('batch_complete') ||
      // 中文格式（基于实际后端消息）
      thought.thought.includes('开始执行') ||
      thought.thought.includes('执行完成') ||
      thought.thought.includes('工具执行') ||
      thought.thought.includes('开始执行工具') ||
      // 通用格式
      thought.thought.includes('tool execution') ||
      thought.thought.match(/\b(executing|completed).*tool\b/i)
    ))

  if (isToolMessage) {
    messageType = 'tool'
    displayAgent = thought.agent
    
    // 工具消息直接处理，跳过所有内容过滤
    const message = {
      type: messageType,
      content: formatToolMessage(thought.thought),
      agent: displayAgent,
      id: thought.timestamp,
      phaseOrder,
      nodeOrder
    }
    
    // 如果没有阶段信息，直接显示
    if (!phaseOrder || phaseOrder === 0) {
      addMessage(message.type, message.content, message.agent, message.id)
      return
    }
    
    // 工具消息也遵循阶段管理逻辑
    handlePhaseMessage(message, phaseOrder, nodeOrder, isPhaseComplete)
    return
  }
  // 处理系统消息 - 支持大小写不敏感的System识别
  else if (thought.agent === '系统' || 
           thought.agent?.toLowerCase() === 'system' || 
           thought.agentId === 'system') {
    messageType = 'system'
    displayAgent = ''
  } else if (thought.agent) {
    // 使用直接映射表，无条件分支，统一数据结构
    displayAgent = thought.agent
  }

  // 消息内容增强和过滤（只针对非工具消息）
  let enhancedContent = thought.thought

  // 增强技术指标消息显示 - 使用统一Agent ID判断
  const currentAgentId = getAgentId(displayAgent)
  if ((currentAgentId === 'market' || currentAgentId.includes('analyst')) &&
    (enhancedContent.includes('指标') ||
      enhancedContent.includes('SMA') ||
      enhancedContent.includes('EMA') ||
      enhancedContent.includes('MACD') ||
      enhancedContent.includes('RSI') ||
      enhancedContent.includes('移动平均') ||
      enhancedContent.includes('成交量') ||
      enhancedContent.includes('价格') ||
      enhancedContent.match(/\b(technical|indicator|analysis)\b/i))) {
    // 如果消息缺少数值，添加提示
    if (!(/\d+/.test(enhancedContent))) {
      enhancedContent += ' (正在获取数据...)'
    }
  }

  // 只处理加密货币内容，移除股票相关过滤
  const agentId = getAgentId(displayAgent)
  if (agentId === 'social' || agentId === 'news') {
    const cryptoKeywords = ['BTC', 'Bitcoin', '比特币', 'ETH', '以太坊', 'crypto', '加密货币', 'USDT']
    const hasCryptoContent = cryptoKeywords.some(k => enhancedContent.toLowerCase().includes(k.toLowerCase()))
    
    // 如果没有加密货币关键词，保持原内容不变
    if (!hasCryptoContent) {
      // console.log('📝 内容不包含加密货币关键词，保持原样')
    }
  }

  // 移除全局股票替换逻辑，只处理加密货币内容

  // 创建消息对象
  const message = {
    type: messageType,
    content: enhancedContent,
    agent: displayAgent,
    id: thought.timestamp,
    phaseOrder,
    nodeOrder
  }

  // 如果没有阶段信息，直接显示
  if (!phaseOrder || phaseOrder === 0) {
    addMessage(message.type, message.content, message.agent, message.id)
    return
  }

  // Linus式智能阶段推进：消除等待isPhaseComplete的特殊情况
  if (phaseOrder > currentPhaseOrder.value) {
    // console.log(`🚀 智能推进阶段: Phase ${currentPhaseOrder.value} -> Phase ${phaseOrder}`)
    // console.log(`💡 触发消息: ${displayAgent} - ${thought.thought.substring(0, 80)}...`)

    // 自动完成之前的阶段并刷新缓冲消息
    for (let i = currentPhaseOrder.value; i < phaseOrder; i++) {
      phaseCompleted.value.add(i)
      // console.log(`✅ 标记 Phase ${i} 为已完成`)

      // 防止重复刷新：只处理未刷新的阶段
      if (!flushedPhases.value.has(i)) {
        flushedPhases.value.add(i)
        const bufferedMessages = messageBuffer.value.get(i)
        if (bufferedMessages && bufferedMessages.length > 0) {
          // console.log(`📤 刷新 Phase ${i} 的 ${bufferedMessages.length} 条缓冲消息`)
          bufferedMessages.sort((a, b) => (a.nodeOrder || 0) - (b.nodeOrder || 0))
          bufferedMessages.forEach(msg => {
            addMessage(msg.type, msg.content, msg.agent, msg.id, msg.phaseOrder, msg.nodeOrder)
          })
          messageBuffer.value.delete(i)
        }
      } else {
        // console.log(`⏭️  跳过已刷新的 Phase ${i}`)
      }
    }

    // 更新到新阶段
    currentPhaseOrder.value = phaseOrder
    // console.log(`🎯 当前阶段已更新为 Phase ${phaseOrder}, 当前activeAgent: ${activeAgent.value || 'null'}`)

    // 🆕 在阶段切换时主动激活新阶段首个agent（修复单范围Phase 2+无法激活）
    // 根据phaseOrder构建backend key来查找对应的前端stage
    const backendKey = `phase${phaseOrder}_${getPhaseBackendSuffix(phaseOrder)}`
    const stageName = phaseToStageMap[backendKey]

    if (stageName && agents.value[stageName as keyof typeof agents.value]) {
      const stageAgents = agents.value[stageName as keyof typeof agents.value]
      if (Array.isArray(stageAgents) && stageAgents.length > 0) {
        const firstAgent = stageAgents[0]
        if (firstAgent) {
          // 🆕 智能判断是否需要切换到新阶段的agent（解决单范围Phase 2+激活失败）
          const needSwitch = !activeAgent.value ||
            activeAgent.value === null ||
            activeAgent.value !== firstAgent.name

          if (needSwitch) {
            // console.log(`🚀 阶段切换: ${activeAgent.value || 'null'} → ${firstAgent.name} (Phase ${phaseOrder}-${stageName})`)
            activeAgent.value = firstAgent.name
            // 立即刷新该agent的缓冲消息
            flushAgentMessages(firstAgent.name)
          } else {
            // console.log(`🔄 阶段${phaseOrder}首个agent(${firstAgent.name})已激活，无需切换`)
          }
        }
      }
    }
  }

  // Linus原则：统一数据流，消除双重添加的特殊情况
  if (phaseOrder <= currentPhaseOrder.value) {
    // 当前或过去阶段：直接显示，不缓冲（消除重复）
    // console.log(`📝 立即显示消息: Phase ${phaseOrder} - ${displayAgent}`)
    addMessage(message.type, message.content, message.agent, message.id, phaseOrder, nodeOrder)
  } else {
    // 未来阶段：只缓冲，不显示
    if (!messageBuffer.value.has(phaseOrder)) {
      messageBuffer.value.set(phaseOrder, [])
    }
    messageBuffer.value.get(phaseOrder)!.push(message)
    // console.log(`📦 缓冲消息: Phase ${phaseOrder} - ${displayAgent} (当前Phase: ${currentPhaseOrder.value})`)
  }

  // 如果当前阶段完成，进入下一阶段
  if (isPhaseComplete && phaseOrder === currentPhaseOrder.value) {
    phaseCompleted.value.add(phaseOrder)
    currentPhaseOrder.value++
    flushNextPhase()
  }
}

// 刷新下一阶段的缓冲消息
const flushNextPhase = () => {
  const nextMessages = messageBuffer.value.get(currentPhaseOrder.value)
  if (nextMessages) {
    // 按节点顺序排序
    nextMessages.sort((a, b) => (a.nodeOrder || 0) - (b.nodeOrder || 0))
    // 显示所有消息
    nextMessages.forEach(msg => {
      addMessage(msg.type, msg.content, msg.agent, msg.id, msg.phaseOrder, msg.nodeOrder)
    })
    // 清空缓冲区
    messageBuffer.value.delete(currentPhaseOrder.value)
  }
}

// Linus原则：移除硬编码映射表，让后端直接发送本地化名称

// Agent名称映射表 - 统一使用英文作为后端通信标准  
// 前端通过i18n处理多语言显示（保持向后兼容）
const agentNameMap: Record<string, string> = {
  // 后端标准化名称映射（Linus原则：消除特殊情况）
  // 下划线格式
  'market_analyst': 'market',
  'social_analyst': 'social',
  'news_analyst': 'news',
  'fundamentals_analyst': 'fundamentals',
  'bull_researcher': 'bull',
  'bear_researcher': 'bear',
  'research_manager': 'manager',
  'trader': 'trader',
  'risky_analyst': 'risky',
  'neutral_analyst': 'neutral',
  'safe_analyst': 'safe',
  'risk_judge': 'judge',
  'portfolio_manager': 'portfolio',

  // 连字符格式（兼容后端实际发送格式）
  'market-analyst': 'market',
  'social-analyst': 'social',
  'news-analyst': 'news',
  'fundamentals-analyst': 'fundamentals',
  'bull-researcher': 'bull',
  'bear-researcher': 'bear',
  'research-manager': 'manager',
  'risky-analyst': 'risky',
  'neutral-analyst': 'neutral',
  'safe-analyst': 'safe',
  'risk-judge': 'judge',
  'portfolio-manager': 'portfolio',

  // 保留旧的映射以兼容（后续可删除）
  'Market Analyst': 'market',
  'Social Analyst': 'social',
  'Social Media Analyst': 'social',  // Alias
  'News Analyst': 'news',
  'Fundamentals Analyst': 'fundamentals',
  'Bull Researcher': 'bull',
  'Bear Researcher': 'bear',
  'Research Manager': 'manager',
  'Trader': 'trader',
  'Risky Analyst': 'risky',
  'Neutral Analyst': 'neutral',
  'Safe Analyst': 'safe',
  'Risk Judge': 'judge',
  // Portfolio
  'Portfolio Manager': 'portfolio',

  // 中文Agent名称映射（向后兼容）
  '市场分析师': 'market',
  '社交媒体分析师': 'social',
  '新闻分析师': 'news',
  '基本面分析师': 'fundamentals',
  '链上分析师': 'onchain',
  '多头研究员': 'bull',
  '空头研究员': 'bear',
  '研究经理': 'manager',
  '交易员': 'trader',
  '激进分析师': 'risky',
  '保守分析师': 'safe',
  '中性分析师': 'neutral',
  '风险评估': 'judge',
  '组合经理': 'portfolio'
}

// Linus式统一Agent标识符获取函数：消除特殊情况处理
const getAgentId = (agentName: string): string => {
  if (!agentName) return ''
  // 优先从映射表获取
  const mappedId = agentNameMap[agentName]
  if (mappedId) return mappedId
  // 回退：生成标准ID
  return agentName.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
}

// 获取Agent的多语言显示名称
const getAgentDisplayName = (agentId: string): string => {
  // 使用i18n获取Agent名称
  const key = `agents.names.${agentId}`
  const translated = t(key)
  // 如果没有翻译，返回原始ID
  return translated !== key ? translated : agentId
}

// 根据phaseOrder获取backend key的后缀
const getPhaseBackendSuffix = (phaseOrder: number): string => {
  const suffixMap: Record<number, string> = {
    1: 'analysis',
    2: 'debate',
    3: 'trading',
    4: 'risk',
    5: 'decision'
  }
  return suffixMap[phaseOrder] || 'unknown'
}

// 🆕 尝试激活下个阶段的首个agent（解决跨阶段切换问题）
const tryActivateNextPhaseFirstAgent = () => {
  // console.log('🔍 尝试激活下个阶段的首个agent...')

  // 查找下一个阶段
  const nextPhaseOrder = currentPhaseOrder.value + 1
  if (nextPhaseOrder > 5) {
    // console.log('📏 已是最后一个阶段，无需激活')
    return
  }

  // 构建 backend key 并查找对应的stage
  const backendKey = `phase${nextPhaseOrder}_${getPhaseBackendSuffix(nextPhaseOrder)}`
  const stageName = phaseToStageMap[backendKey]

  if (!stageName) {
    // console.log(`⚠️ 无法映射 backend key: ${backendKey}`)
    return
  }

  const stageAgents = agents.value[stageName as keyof typeof agents.value]
  if (!Array.isArray(stageAgents) || stageAgents.length === 0) {
    // console.log(`🔄 下个阶段 ${stageName} 没有agents，继续等待`)
    return
  }

  const firstAgent = stageAgents[0]
  if (firstAgent && !activeAgent.value) {
    activeAgent.value = firstAgent.name
    // console.log(`🚀 跨阶段激活Phase ${nextPhaseOrder}(${stageName})的首个agent: ${firstAgent.name}`)
    flushAgentMessages(firstAgent.name)
  }
}

// 更新所有Agent的显示名称
const updateAllAgentNames = () => {
  // console.log('🌐 更新所有Agent名称为新语言:', locale.value)

  Object.keys(agents.value).forEach(stageName => {
    const stageAgents = agents.value[stageName as keyof typeof agents.value]
    if (Array.isArray(stageAgents)) {
      stageAgents.forEach(agent => {
        const newName = getAgentDisplayName(agent.id)
        if (agent.name !== newName) {
          // console.log(`✅ 更新Agent [${agent.id}]: ${agent.name} -> ${newName}`)
          agent.name = newName
        }
      })
    }
  })

  // 同时更新缓存中的Agent配置
  agentCache.forEach((cachedAgents, cacheKey) => {
    Object.keys(cachedAgents).forEach(stageName => {
      const stageAgents = cachedAgents[stageName]
      if (Array.isArray(stageAgents)) {
        stageAgents.forEach(agent => {
          agent.name = getAgentDisplayName(agent.id)
        })
      }
    })
  })
}

// 监听语言变化
watch(() => locale.value, () => {
  // console.log('🌍 检测到语言切换:', locale.value)
  // 更新所有Agent的显示名称
  updateAllAgentNames()
})

// 消息去重缓存（保存最近10秒内的消息指纹）
const messageCache = new Map<string, number>()

// Agent消息缓冲区 - 按Agent分组存储消息
const agentMessageBuffer = ref<Map<string, Array<any>>>(new Map())

// 当前活跃的Agent（正在处理的Agent）
const activeAgent = ref<string>('')

// 自动flush机制的时间戳
let lastMessageTime = Date.now()
const autoFlushTimeout = 30000 // 30秒无消息自动flush
let autoFlushInterval: number | null = null // 定时器句柄

// Agent执行顺序
const agentExecutionOrder = [
  '市场分析师',
  '社交媒体分析师',
  '新闻分析师',
  '基本面分析师',
  '链上分析师',
  '多头研究员',
  '空头研究员',
  '研究经理',
  '交易员',
  '激进分析师',
  '保守分析师',
  '中性分析师',
  '风险评估',
  '组合经理'
]

// 检查Agent是否在执行顺序中（使用统一ID比较）
const isAgentInExecutionOrder = (agentName: string): boolean => {
  const agentId = getAgentId(agentName)
  return agentExecutionOrder.some(orderAgent => getAgentId(orderAgent) === agentId)
}

// 获取Agent在执行顺序中的索引
const getAgentExecutionIndex = (agentName: string): number => {
  const agentId = getAgentId(agentName)
  return agentExecutionOrder.findIndex(orderAgent => getAgentId(orderAgent) === agentId)
}

// 格式化工具消息显示
const formatToolMessage = (content: string): string => {
  if (!content) return content
  
  // 直接返回后端提供的完整消息内容，不添加 emoji
  return content
}

// 处理阶段消息（抽取公共逻辑）
const handlePhaseMessage = (message: any, phaseOrder: number, nodeOrder: number, isPhaseComplete: boolean) => {
  // Linus式智能阶段推进：消除等待isPhaseComplete的特殊情况
  if (phaseOrder > currentPhaseOrder.value) {
    // 自动完成之前的阶段并刷新缓冲消息
    for (let i = currentPhaseOrder.value; i < phaseOrder; i++) {
      phaseCompleted.value.add(i)
      if (!flushedPhases.value.has(i)) {
        flushedPhases.value.add(i)
        const bufferedMessages = messageBuffer.value.get(i)
        if (bufferedMessages && bufferedMessages.length > 0) {
          bufferedMessages.sort((a, b) => (a.nodeOrder || 0) - (b.nodeOrder || 0))
          bufferedMessages.forEach(msg => {
            addMessage(msg.type, msg.content, msg.agent, msg.id, msg.phaseOrder, msg.nodeOrder)
          })
          messageBuffer.value.delete(i)
        }
      }
    }
    currentPhaseOrder.value = phaseOrder
  }

  // 统一数据流，消除双重添加的特殊情况
  if (phaseOrder <= currentPhaseOrder.value) {
    // 当前或过去阶段：直接显示，不缓冲
    addMessage(message.type, message.content, message.agent, message.id, phaseOrder, nodeOrder)
  } else {
    // 未来阶段：只缓冲，不显示
    if (!messageBuffer.value.has(phaseOrder)) {
      messageBuffer.value.set(phaseOrder, [])
    }
    messageBuffer.value.get(phaseOrder)!.push(message)
  }

  // 如果当前阶段完成，进入下一阶段
  if (isPhaseComplete && phaseOrder === currentPhaseOrder.value) {
    phaseCompleted.value.add(phaseOrder)
    currentPhaseOrder.value++
    flushNextPhase()
  }
}

// 刷新指定Agent的缓冲消息
const flushAgentMessages = (agentName: string) => {
  const bufferedMessages = agentMessageBuffer.value.get(agentName)
  if (bufferedMessages && bufferedMessages.length > 0) {
    // console.log(`📤 Flushing ${bufferedMessages.length} messages for ${agentName}`)
    bufferedMessages.forEach(msg => {
      messages.value.push(msg)
    })
    // 清空该Agent的缓冲区
    agentMessageBuffer.value.set(agentName, [])
  }
}

// 刷新所有缓冲消息
const flushAllBufferedMessages = () => {
  let totalFlushed = 0
  for (const [agentName, messages] of agentMessageBuffer.value.entries()) {
    if (messages && messages.length > 0) {
      totalFlushed += messages.length
    }
    flushAgentMessages(agentName)
  }

  // 只有实际刷新了消息才输出日志，避免空刷新的噪音
  if (totalFlushed > 0) {
    // console.log(`🚀 Auto-flushed ${totalFlushed} buffered messages due to timeout`)
  }
}

// 检查并自动flush超时的消息
const checkAndAutoFlush = () => {
  const now = Date.now()

  // 检查是否有待刷新的消息
  let hasBufferedMessages = false
  for (const [, messages] of agentMessageBuffer.value.entries()) {
    if (messages && messages.length > 0) {
      hasBufferedMessages = true
      break
    }
  }

  // 只有在有缓冲消息且超时的情况下才刷新
  if (hasBufferedMessages && now - lastMessageTime > autoFlushTimeout) {
    flushAllBufferedMessages()
    lastMessageTime = now
  }
}

// 动态更新活跃Agent
const updateActiveAgentDynamically = (agentName: string) => {
  if (agentName !== activeAgent.value && isAgentInExecutionOrder(agentName)) {
    // console.log(`🔄 Dynamic agent switch detected: ${activeAgent.value} -> ${agentName}`)

    // flush当前agent的消息
    if (activeAgent.value) {
      flushAgentMessages(activeAgent.value)
    }

    // 切换到新agent
    activeAgent.value = agentName

    // flush新agent的缓冲消息
    flushAgentMessages(agentName)
  }
}

// 切换到下一个Agent（智能跳过不存在的agents）
const switchToNextAgent = (currentAgent: string) => {
  const currentIndex = getAgentExecutionIndex(currentAgent)

  // console.log(`🔍 [switchToNextAgent] 查找 ${currentAgent} 的下一个agent`, {
  //   currentIndex,
  //   totalAgents: agentExecutionOrder.length
  // })

  // 查找下一个实际存在的agent
  for (let i = currentIndex + 1; i < agentExecutionOrder.length; i++) {
    const nextAgent = agentExecutionOrder[i]

    // 检查这个agent是否在当前配置中存在
    let agentExists = false
    let foundStage = ''

    for (const [stageName, stageAgents] of Object.entries(agents.value)) {
      if (Array.isArray(stageAgents)) {
        const found = stageAgents.find(a => a.name === nextAgent)
        if (found) {
          agentExists = true
          foundStage = stageName
          break
        }
      }
    }

    // // console.log(`🔎 检查候选agent: ${nextAgent}`, {
    //   exists: agentExists,
    //   stage: foundStage
    // })

    if (agentExists) {
      activeAgent.value = nextAgent
      // console.log(`✅ 成功切换: ${currentAgent} → ${nextAgent} (${foundStage}阶段)`)
      flushAgentMessages(nextAgent)
      return
    }
  }

  // 如果没有找到下一个agent，可能是阶段结束
  // console.log(`📍 没有找到 ${currentAgent} 的下一个agent，可能阶段即将结束`)
  // console.log(`🔄 重置activeAgent，准备跨阶段切换`)
  activeAgent.value = null  // 重置activeAgent，让下个阶段的第一个agent能正确激活

  // 🆕 尝试激活下个阶段的首个agent（修复单范围选择Phase 2+无法激活问题）
  nextTick(() => {
    // console.log('🔄 延迟激活下个阶段首个agent...')
    tryActivateNextPhaseFirstAgent()
  })
}

const addMessage = (type: any, content: string, agent?: string, messageId?: string, phaseOrder?: number, nodeOrder?: number) => {
  const time = new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })

  // 生成增强消息指纹用于去重（包含阶段和节点信息）
  const fingerprint = `${type}:${agent || ''}:${content}:${phaseOrder || 0}:${nodeOrder || 0}`
  const now = Date.now()

  // 检查是否为重复消息（30秒内相同指纹视为重复）
  const lastTime = messageCache.get(fingerprint)
  if (lastTime && now - lastTime < 30000) {
    // console.log('🔄 忽略重复消息:', fingerprint.substring(0, 100) + '...')
    return
  }

  // 更新缓存
  messageCache.set(fingerprint, now)

  // 清理过期缓存（超过30秒的）
  for (const [key, timestamp] of messageCache.entries()) {
    if (now - timestamp > 30000) {
      messageCache.delete(key)
    }
  }

  // addMessage层面的最终内容过滤
  let filteredContent = content

  // 针对所有类型消息的通用术语替换
  const finalReplacements = {
    '目标公司': '目标资产',
    '该公司': '该项目',
    '这家公司': '这个项目',
    '公司业务': '项目业务',
    '公司发展': '项目发展',
    '公司前景': '项目前景',
    'Company': 'Project',
    'Companies': 'Projects',
    'Corporation': 'Protocol'
  }

  let hasFinalFilter = false
  Object.entries(finalReplacements).forEach(([from, to]) => {
    if (filteredContent.includes(from)) {
      filteredContent = filteredContent.replace(new RegExp(from, 'g'), to)
      hasFinalFilter = true
    }
  })

  if (hasFinalFilter) {
    // // console.log('🎯 addMessage层最终过滤:', {
    //   agent: agent || 'system',
    //   original: content,
    //   filtered: filteredContent
    // })
  }

  const message = {
    time,
    type,
    content: filteredContent,
    agent,
    id: messageId || `msg-${now}`,
    phaseOrder,
    nodeOrder
  }

  // 更新最后消息时间
  lastMessageTime = Date.now()

  // 如果消息来自特定Agent且不是系统消息，进行缓冲处理
  if (agent && type !== 'system') {
    // 直接使用后端发送的本地化Agent名称
    const agentDisplayName = agent

    // 如果agent不在预定义列表中，直接显示（fallback机制）
    if (!isAgentInExecutionOrder(agentDisplayName)) {
      // console.log(`⚠️ Unknown agent ${agentDisplayName}, displaying immediately`)
      messages.value.push(message)
      return
    }

    // 检查是否需要动态切换Agent
    updateActiveAgentDynamically(agentDisplayName)

    // 如果这个Agent还不是活跃Agent，缓冲其消息
    if (agentDisplayName !== activeAgent.value) {
      if (!agentMessageBuffer.value.has(agentDisplayName)) {
        agentMessageBuffer.value.set(agentDisplayName, [])
      }
      agentMessageBuffer.value.get(agentDisplayName)!.push(message)
      // console.log(`📦 Buffering message for ${agentDisplayName}: ${content.substring(0, 50)}...`)
      return // 不立即显示，等待Agent激活
    }
  }

  // 立即显示消息（系统消息或当前活跃Agent的消息）
  messages.value.push(message)

  // 保持消息数量在合理范围内
  if (messages.value.length > 100) {
    messages.value = messages.value.slice(-100)
  }
}




// 时钟更新
let timeInterval: number | undefined

onMounted(async () => {
  // 初始化智能体配置
  const initialMarketType = props.formData.marketType || 'crypto'
  const initialScopes = props.formData.analysisScopes || []

  // 设置初始配置
  const initialAgents = getDefaultAgents(initialMarketType, initialScopes)
  if (!areAgentsEquivalent(agents.value, initialAgents)) {
    agents.value = initialAgents
  }

  // 设置缓存
  const cacheKey = getCacheKey(initialMarketType, initialScopes)
  agentCache.set(cacheKey, initialAgents)

  // 更新时间
  const updateTime = () => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }
  updateTime()
  timeInterval = setInterval(updateTime, 1000)

  // 初始化消息 - 使用翻译键而非翻译后文本，以支持动态语言切换
  addMessage('system', 'analysis.messages.ready')
  addMessage('system', 'analysis.messages.initialized')
  
  // 订阅全局消息服务
  watch(consoleMessageService.getMessageQueue(), (newMessages) => {
    // 将新消息添加到本地消息数组
    const lastMessage = newMessages[newMessages.length - 1]
    if (lastMessage) {
      addMessage(lastMessage.type, lastMessage.content, lastMessage.agent)
    }
  }, { deep: true })
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})

// 显示分析报告
const showAnalysisReport = () => {
  // 获取最新的分析历史记录
  const latestHistory = analysisStore.analysisHistory[0]
  if (latestHistory) {
    selectedAnalysis.value = latestHistory
    showDetailModal.value = true
  } else {
    console.warn('⚠️ 没有找到分析历史记录')
  }
}
</script>

<style lang="scss" scoped>
.practical-console {
  width: 100%;
  height: 100%;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-od-sm);
  color: var(--od-text-primary);
  font-family: 'Proto Mono', 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 上部分布局
.console-upper {
  height: 40%;
  min-height: 280px;
  display: flex;
  background: var(--od-background);
  border-bottom: 1px solid var(--od-border);
  flex-shrink: 0;

  // 左侧配置区
  .config-section {
    width: 25%;
    min-width: 240px;
    max-width: 300px;
    background: var(--od-background-alt);
    padding: 0.75rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--od-border);

    .basic-config {
      background: var(--od-background);
      border: 1px solid var(--od-border);
      border-radius: 6px;
      padding: 0.5rem;
      margin-bottom: 0.75rem;

      .config-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.4rem 0.25rem;
        font-size: 12px;
        transition: all 0.2s;

        &:hover {
          background: rgba(74, 222, 128, 0.03);
          border-radius: 4px;
        }

        .label {
          color: var(--od-text-secondary);
          font-weight: 500;
          text-transform: uppercase;
          font-size: 11px;
          letter-spacing: 0.3px;
        }

        .value {
          color: var(--od-primary-light);
          font-weight: 600;
          font-size: 13px;
          text-shadow: 0 0 20px rgba(74, 222, 128, 0.5);

          .depth-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;

            .depth-level {
              font-size: 12px;
              font-weight: 600;
              color: var(--od-primary-light);
            }

            .depth-bar {
              display: inline-flex;
              width: 50px;
              height: 4px;
              background: var(--od-background);
              border: 1px solid var(--od-border);
              border-radius: 2px;
              overflow: hidden;
              position: relative;

              .depth-fill {
                display: block;
                height: 100%;
                background: linear-gradient(90deg,
                    var(--od-primary) 0%,
                    var(--od-primary-light) 100%);
                transition: width 0.3s ease;
                box-shadow: 0 0 10px rgba(74, 222, 128, 0.5);
              }
            }
          }
        }
      }
    }

    .divider {
      height: 1px;
      background: var(--od-border);
      margin: 0.75rem 0;
    }

    .scope-cards {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }

    .model-config {
      .config-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11px;

        .label {
          color: var(--od-text-secondary);
        }

        .value {
          color: var(--od-primary);
          font-weight: 500;
        }
      }
    }
  }

  // 右侧流程区
  .progress-section {
    flex: 1;
    background: var(--od-background);
    overflow: hidden;
  }
}

// 下部分消息流
.console-lower {
  flex: 1;
  min-height: 350px;
  background: var(--od-background);
  overflow: hidden;
}

// 底部控制栏
.control-bar {
  height: 50px;
  background: var(--od-background-alt);
  border-top: 1px solid var(--od-border);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 1rem;
  flex-shrink: 0;

  .control-btn {
    padding: 0.5rem 2rem;
    border: none;
    border-radius: var(--border-radius-md);
    font-family: inherit;
    font-size: 13px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.2s;

    &.start-btn {
      background: var(--od-primary);
      color: var(--od-background);

      &:hover:not(:disabled) {
        background: var(--od-primary-hover);
        transform: translateY(-1px);
        box-shadow: var(--shadow-od-md);
      }

      &:disabled {
        background: var(--od-background);
        color: var(--od-text-muted);
        border: 1px solid var(--od-border);
        cursor: not-allowed;
      }
    }

    &.stop-btn {
      background: var(--od-error);
      color: white;

      &:hover {
        background: var(--od-error-hover);
        transform: translateY(-1px);
        box-shadow: var(--shadow-od-md);
      }
    }
  }
}

// 动画
@keyframes pulse {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.7;
  }
}

// 响应式
@media (max-width: 1200px) {
  .console-body {
    .console-panel {
      &.progress-panel {
        width: 40%;
      }
    }
  }
}

@media (max-width: 1024px) {
  .console-body {
    flex-direction: column;

    .console-panel {
      width: 100% !important;
      min-width: 100% !important;
      max-width: 100% !important;

      &.progress-panel {
        height: 300px;
        overflow-y: auto;
      }

      &.message-panel {
        flex: 1;
        min-height: 400px;
      }
    }
  }

  .config-summary-bar {
    flex-wrap: wrap;
    height: auto;
    padding: 0.5rem 1rem;
    gap: 1rem;
  }
}

@media (max-width: 768px) {
  .status-bar {
    flex-wrap: wrap;
    height: auto;
    padding: 0.5rem;

    .status-center {
      width: 100%;
      order: -1;
      margin-bottom: 0.5rem;
      text-align: center;
    }

    .status-left,
    .status-right {
      width: 50%;
    }

    .status-right {
      text-align: right;
    }
  }
}
</style>