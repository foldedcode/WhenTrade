<template>
  <div class="dynamic-analysis-panel">
    <!-- 分析配置阶段 -->
    <div v-if="stage === 'config'" class="config-stage">
      <DynamicDomainSelector 
        @domains-selected="onDomainsSelected"
      />
    </div>

    <!-- 分析进行阶段 -->
    <div v-else-if="stage === 'analysis'" class="analysis-stage">
      <div class="analysis-header">
        <div class="analysis-info">
          <h2 class="analysis-title">{{ analysisTitle }}</h2>
          <div class="analysis-meta">
            <span class="meta-item">
              <i class="i-carbon-chart-multitype"></i>
              {{ selectedDomains.length }} {{ t('analysis.domains.selected') }}
            </span>
            <span class="meta-item">
              <i class="i-carbon-user-multiple"></i>
              {{ activeAgentCount }} {{ t('analysis.agents.active') }}
            </span>
            <span class="meta-item">
              <i class="i-carbon-globe"></i>
              {{ marketTypeLabel }}
            </span>
          </div>
        </div>
        <div class="analysis-actions">
          <button @click="pauseAnalysis" class="action-button" v-if="!isPaused">
            <i class="i-carbon-pause"></i>
            {{ t('analysis.pause') }}
          </button>
          <button @click="resumeAnalysis" class="action-button" v-else>
            <i class="i-carbon-play"></i>
            {{ t('analysis.resume') }}
          </button>
          <button @click="stopAnalysis" class="action-button danger">
            <i class="i-carbon-stop"></i>
            {{ t('analysis.stop') }}
          </button>
        </div>
      </div>

      <div class="analysis-content">
        <!-- 左侧：Agent状态和进度 -->
        <div class="agents-panel">
          <h3 class="panel-title">{{ t('analysis.agents.title') }}</h3>
          <div class="agents-list">
            <div 
              v-for="agent in agents" 
              :key="agent.id"
              class="agent-card"
              :class="{ active: agent.status === 'active' }"
            >
              <div class="agent-header">
                <span class="agent-avatar" :style="{ backgroundColor: agent.color }">
                  {{ agent.name.charAt(0) }}
                </span>
                <div class="agent-info">
                  <div class="agent-name">{{ agent.name }}</div>
                  <div class="agent-domain">{{ agent.domain }}</div>
                </div>
                <div class="agent-status" :class="`status-${agent.status}`">
                  <i :class="getStatusIcon(agent.status)"></i>
                </div>
              </div>
              <div v-if="agent.currentThought" class="agent-current-thought">
                <span class="thought-type">{{ agent.currentThought.type }}:</span>
                <span class="thought-preview">{{ agent.currentThought.content }}</span>
              </div>
              <div class="agent-stats">
                <span class="stat">
                  <i class="i-carbon-brain"></i>
                  {{ agent.thoughtCount }}
                </span>
                <span class="stat">
                  <i class="i-carbon-timer"></i>
                  {{ formatDuration(agent.startTime ?? Date.now()) }}
                </span>
              </div>
            </div>
          </div>

          <!-- 分析阶段进度 -->
          <div class="stage-progress">
            <h4 class="progress-title">{{ t('analysis.progress.title') }}</h4>
            <div class="progress-stages">
              <div 
                v-for="(stage, index) in analysisStages" 
                :key="stage.id"
                class="progress-stage"
                :class="{ 
                  completed: stage.status === 'completed',
                  active: stage.status === 'active',
                  pending: stage.status === 'pending'
                }"
              >
                <div class="stage-indicator">
                  <div class="stage-number">{{ index + 1 }}</div>
                  <div class="stage-line" v-if="index < analysisStages.length - 1"></div>
                </div>
                <div class="stage-content">
                  <div class="stage-name">{{ stage.name }}</div>
                  <div class="stage-agents">{{ stage.agentCount }} agents</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：思考流可视化 -->
        <div class="thought-stream-panel">
          <div class="placeholder-message">
            思考流可视化区域
          </div>
        </div>
      </div>
    </div>

    <!-- 分析完成阶段 -->
    <div v-else-if="stage === 'completed'" class="completed-stage">
      <div class="completion-header">
        <i class="i-carbon-checkmark-filled completion-icon"></i>
        <h2 class="completion-title">{{ t('analysis.completed.title') }}</h2>
      </div>
      <div class="completion-summary">
        <div class="summary-stats">
          <div class="summary-stat">
            <div class="stat-value">{{ totalThoughts }}</div>
            <div class="stat-label">{{ t('analysis.completed.thoughts') }}</div>
          </div>
          <div class="summary-stat">
            <div class="stat-value">{{ agents.length }}</div>
            <div class="stat-label">{{ t('analysis.completed.agents') }}</div>
          </div>
          <div class="summary-stat">
            <div class="stat-value">{{ formatDuration(analysisStartTime) }}</div>
            <div class="stat-label">{{ t('analysis.completed.duration') }}</div>
          </div>
        </div>
      </div>
      <div class="completion-actions">
        <button @click="viewReport" class="primary-button">
          <i class="i-carbon-document"></i>
          {{ t('analysis.completed.viewReport') }}
        </button>
        <button @click="startNewAnalysis" class="secondary-button">
          <i class="i-carbon-add"></i>
          {{ t('analysis.completed.newAnalysis') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import DynamicDomainSelector from './DynamicDomainSelector.vue'
import { useAnalysisStore } from '@/stores/analysis'
import { useWebSocket } from '@/composables/useWebSocket'
import type { Agent, AnalysisStage, AgentThought } from '@/types/analysis'

const { t } = useI18n()
const router = useRouter()
const analysisStore = useAnalysisStore()
const { send, subscribe } = useWebSocket()

// 分析阶段：config -> analysis -> completed
const stage = ref<'config' | 'analysis' | 'completed'>('config')

// 分析配置
const selectedDomains = ref<string[]>([])
const selectedMarketType = ref<string>('')
const scenarioDescription = ref<string>('')
const currentAnalysisId = ref<string>('')

// 分析状态
const agents = ref<Agent[]>([])
const analysisStages = ref<AnalysisStage[]>([])
const initialThoughts = ref<AgentThought[]>([])
const isPaused = ref(false)
const analysisStartTime = ref(Date.now())
const totalThoughts = ref(0)

// 计算属性
const activeAgentCount = computed(() => 
  agents.value.filter(a => a.status === 'active').length
)

const marketTypeLabel = computed(() => {
  const labels: Record<string, string> = {
    crypto: t('analysis.marketTypes.crypto'),
  }
  return labels[selectedMarketType.value] || selectedMarketType.value
})

const analysisTitle = computed(() => {
  if (scenarioDescription.value) {
    return scenarioDescription.value.slice(0, 50) + '...'
  }
  return t('analysis.defaultTitle')
})

// 方法
const onDomainsSelected = async (domains: string[], marketType: string, scenario?: string) => {
  selectedDomains.value = domains
  selectedMarketType.value = marketType
  scenarioDescription.value = scenario || ''
  
  // 开始分析
  await startAnalysis()
}

const startAnalysis = async () => {
  try {
    // 调用API创建分析任务
    const response = await analysisStore.createAnalysis({
      symbol: 'BTC', // 这里应该从其他地方获取
      marketType: selectedMarketType.value,
      domains: selectedDomains.value,
      scenario: scenarioDescription.value,
      enableDynamic: true
    })
    
    currentAnalysisId.value = response.analysisId
    // 确保状态类型正确
    agents.value = response.agents.map((agent: any) => ({
      ...agent,
      status: ['idle', 'active', 'completed'].includes(agent.status) ? agent.status : 'idle'
    }))
    analysisStages.value = response.stages.map((stage: any) => ({
      ...stage,
      status: ['pending', 'active', 'completed'].includes(stage.status) ? stage.status : 'pending'
    }))
    
    // 订阅WebSocket事件
    subscribe('analysis.update', handleAnalysisUpdate)
    subscribe('agent.thought', handleThoughtMessage)
    
    // 切换到分析阶段
    stage.value = 'analysis'
    analysisStartTime.value = Date.now()
  } catch (error) {
    console.error('Failed to start analysis:', error)
    // 处理错误
  }
}

const pauseAnalysis = () => {
  send('analysis.control', {
    analysisId: currentAnalysisId.value,
    action: 'pause'
  })
  isPaused.value = true
}

const resumeAnalysis = () => {
  send('analysis.control', {
    analysisId: currentAnalysisId.value,
    action: 'resume'
  })
  isPaused.value = false
}

const stopAnalysis = () => {
  if (confirm(t('analysis.confirmStop'))) {
    send('analysis.control', {
      analysisId: currentAnalysisId.value,
      action: 'stop'
    })
    handleAnalysisComplete()
  }
}

const handleAnalysisComplete = () => {
  stage.value = 'completed'
  // 订阅在useWebSocket中会自动清理
}

const viewReport = () => {
  router.push(`/report/${currentAnalysisId.value}`)
}

const startNewAnalysis = () => {
  // 重置状态
  stage.value = 'config'
  selectedDomains.value = []
  selectedMarketType.value = ''
  scenarioDescription.value = ''
  currentAnalysisId.value = ''
  agents.value = []
  analysisStages.value = []
  initialThoughts.value = []
  totalThoughts.value = 0
}

// 工具方法
const getStatusIcon = (status: string): string => {
  const iconMap: Record<string, string> = {
    active: 'i-carbon-dot-mark animate-pulse',
    idle: 'i-carbon-circle',
    completed: 'i-carbon-checkmark-filled'
  }
  return iconMap[status] || 'i-carbon-circle'
}

const formatDuration = (startTime: number | undefined): string => {
  if (!startTime) return '0:00'
  const duration = Date.now() - startTime
  const minutes = Math.floor(duration / 60000)
  const seconds = Math.floor((duration % 60000) / 1000)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

// WebSocket消息处理
const handleAnalysisUpdate = (data: any) => {
  if (data.type === 'agent_update') {
    const agent = agents.value.find(a => a.id === data.agentId)
    if (agent) {
      Object.assign(agent, data.update)
    }
  } else if (data.type === 'stage_update') {
    const stage = analysisStages.value.find(s => s.id === data.stageId)
    if (stage) {
      stage.status = data.status
    }
  } else if (data.type === 'analysis_complete') {
    handleAnalysisComplete()
  }
}

const handleThoughtMessage = (data: any) => {
  if (data.thought) {
    totalThoughts.value++
    // 更新agent的当前思考
    const agent = agents.value.find(a => a.id === data.thought.agentId)
    if (agent) {
      agent.currentThought = {
        type: data.thought.thoughtType,
        content: data.thought.content
      }
      agent.thoughtCount = (agent.thoughtCount || 0) + 1
    }
  }
}

// 生命周期
onMounted(() => {
  window.addEventListener('ws-message:analysis.update', handleAnalysisUpdate)
  window.addEventListener('ws-message:agent.thought', handleThoughtMessage)
})

onUnmounted(() => {
  window.removeEventListener('ws-message:analysis.update', handleAnalysisUpdate)
  window.removeEventListener('ws-message:agent.thought', handleThoughtMessage)
})
</script>

<style scoped>
.dynamic-analysis-panel {
  @apply h-full;
  background: var(--od-background);
}

/* 配置阶段 */
.config-stage {
  @apply max-w-6xl mx-auto p-6;
}

/* 分析阶段 */
.analysis-stage {
  @apply h-full flex flex-col;
}

.analysis-header {
  @apply flex justify-between items-center p-6;
  background: var(--od-background-alt);
  border-bottom: 1px solid var(--od-border);
}

.analysis-info {
  @apply space-y-2;
}

.analysis-title {
  @apply text-xl font-semibold;
  color: var(--od-text-primary);
}

.analysis-meta {
  @apply flex gap-4;
}

.meta-item {
  @apply flex items-center gap-1 text-sm;
  color: var(--od-text-secondary);
}

.analysis-actions {
  @apply flex gap-3;
}

.action-button {
  @apply flex items-center gap-2 px-4 py-2 rounded-md transition-colors;
  background: var(--od-background);
  border: 1px solid var(--od-border);
  color: var(--od-text-primary);
}

.action-button:hover {
  background: var(--od-background-light);
}

.action-button.danger:hover {
  @apply text-red-500;
  background: rgba(244, 71, 71, 0.1);
  border-color: #f44747;
}

.analysis-content {
  @apply flex-1 flex gap-6 p-6 overflow-hidden;
}

/* Agent面板 */
.agents-panel {
  @apply w-96 flex flex-col gap-6;
}

.panel-title {
  @apply text-lg font-semibold;
  color: var(--od-text-primary);
}

.agents-list {
  @apply space-y-3 overflow-y-auto max-h-96;
}

.agent-card {
  @apply p-4 rounded-lg transition-all;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
}

.agent-card.active {
  border-color: var(--od-primary-light);
  @apply shadow-sm;
}

.agent-header {
  @apply flex items-center gap-3 mb-3;
}

.agent-avatar {
  @apply w-10 h-10 rounded-full flex items-center justify-center 
         text-white font-bold;
}

.agent-info {
  @apply flex-1;
}

.agent-name {
  @apply font-medium;
  color: var(--od-text-primary);
}

.agent-domain {
  @apply text-sm;
  color: var(--od-text-secondary);
}

.agent-status {
  @apply text-xl;
}

.status-active {
  @apply text-green-500;
}

.status-idle {
  @apply text-gray-400;
}

.status-completed {
  @apply text-blue-500;
}

.agent-current-thought {
  @apply mb-2 p-2 rounded text-sm;
  background: var(--od-background);
}

.thought-type {
  @apply mr-1;
  color: var(--od-text-secondary);
}

.thought-preview {
  @apply line-clamp-2;
  color: var(--od-text-primary);
}

.agent-stats {
  @apply flex gap-4 text-sm;
  color: var(--od-text-secondary);
}

.stat {
  @apply flex items-center gap-1;
}

/* 进度追踪 */
.stage-progress {
  @apply p-4 rounded-lg;
  background: var(--od-background-alt);
}

.progress-title {
  @apply font-medium mb-4;
  color: var(--od-text-primary);
}

.progress-stages {
  @apply space-y-3;
}

.progress-stage {
  @apply flex items-center gap-3;
}

.stage-indicator {
  @apply relative;
}

.stage-number {
  @apply w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium;
  background: var(--od-background);
  border: 2px solid var(--od-border);
  color: var(--od-text-secondary);
}

.progress-stage.completed .stage-number {
  background: var(--od-success);
  border-color: var(--od-success);
  @apply text-white;
}

.progress-stage.active .stage-number {
  background: var(--od-primary-light);
  border-color: var(--od-primary-light);
  @apply text-white;
}

.stage-line {
  @apply absolute top-8 left-1/2 -translate-x-1/2 w-0.5 h-8;
  background: var(--od-border);
}

.stage-content {
  @apply flex-1;
}

.stage-name {
  @apply font-medium;
  color: var(--od-text-primary);
}

.stage-agents {
  @apply text-sm;
  color: var(--od-text-secondary);
}

/* 思考流面板 */
.thought-stream-panel {
  @apply flex-1;
}

/* 完成阶段 */
.completed-stage {
  @apply max-w-2xl mx-auto p-12 text-center;
}

.completion-header {
  @apply mb-8;
}

.completion-icon {
  @apply text-6xl mb-4;
  color: var(--od-success);
}

.completion-title {
  @apply text-2xl font-semibold;
  color: var(--od-text-primary);
}

.completion-summary {
  @apply mb-8;
}

.summary-stats {
  @apply flex justify-center gap-12;
}

.summary-stat {
  @apply text-center;
}

.stat-value {
  @apply text-3xl font-bold mb-1;
  color: var(--od-text-primary);
}

.stat-label {
  @apply text-sm;
  color: var(--od-text-secondary);
}

.completion-actions {
  @apply flex justify-center gap-4;
}

.primary-button {
  @apply flex items-center gap-2 px-6 py-3 text-white rounded-md transition-colors;
  background: var(--od-primary-light);
}

.primary-button:hover {
  background: var(--od-primary);
}

.secondary-button {
  @apply flex items-center gap-2 px-6 py-3 rounded-md transition-colors;
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
  color: var(--od-text-primary);
}

.secondary-button:hover {
  background: var(--od-background-light);
}
</style>