<template>
  <div class="agent-collaboration">
    <div class="collaboration-header">
      <h3 class="text-lg font-semibold">{{ $t('collab.title') }}</h3>
      <div class="collaboration-status">
        <span :class="statusClass">{{ statusText }}</span>
      </div>
    </div>

    <!-- 协作阶段指示器 -->
    <div class="collaboration-phases mb-6">
      <div 
        v-for="(phase, index) in phases" 
        :key="index"
        :class="phaseClass(index)"
        class="phase-indicator"
      >
        <div class="phase-icon">
          <i :class="phase.icon"></i>
        </div>
        <div class="phase-info">
          <div class="phase-name">{{ phase.name }}</div>
          <div class="phase-description">{{ phase.description }}</div>
        </div>
      </div>
    </div>

    <!-- 分析师状态面板 -->
    <div class="analysts-panel grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      <div 
        v-for="agent in agents" 
        :key="agent.id"
        class="agent-card"
        :class="agentStatusClass(agent.status)"
      >
        <div class="agent-header">
          <div class="agent-avatar" :style="{ backgroundColor: getAgentColor(agent.type) }">
            <i :class="getAgentIcon(agent.type)"></i>
          </div>
          <div class="agent-info">
            <h4 class="agent-name">{{ agent.name }}</h4>
            <p class="agent-role">{{ agent.role }}</p>
          </div>
          <div class="agent-status-badge">
            <span :class="getStatusBadgeClass(agent.status)">
              {{ getStatusText(agent.status) }}
            </span>
          </div>
        </div>
        
        <div class="agent-progress">
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: agent.progress + '%' }"
            ></div>
          </div>
          <span class="progress-text">{{ agent.progress }}%</span>
        </div>
        
        <div class="agent-current-task">
          <p class="task-text">{{ agent.currentTask }}</p>
        </div>
        
        <div class="agent-confidence">
          <div class="confidence-label">{{ $t('analysis.confidence') }}</div>
          <div class="confidence-value" :class="getConfidenceClass(agent.confidence)">
            {{ (agent.confidence * 100).toFixed(1) }}%
          </div>
        </div>
        
        <!-- 思考过程 -->
        <div v-if="agent.thoughts.length > 0" class="agent-thoughts">
          <div class="thoughts-header">
            <i class="fas fa-brain"></i>
            <span>思考过程</span>
          </div>
          <div class="thoughts-list">
            <div 
              v-for="(thought, index) in agent.thoughts.slice(-3)" 
              :key="index"
              class="thought-item"
            >
              {{ thought }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 辩论区域 -->
    <div v-if="debateActive" class="debate-section">
      <div class="debate-header">
        <h4 class="text-lg font-semibold">
          <i class="fas fa-comments mr-2"></i>
          观点辩论: {{ currentDebateTopic }}
        </h4>
      </div>
      
      <div class="debate-timeline">
        <div 
          v-for="(debate, index) in debates" 
          :key="index"
          class="debate-item"
        >
          <div class="debate-agent">
            <div class="debate-agent-avatar" :style="{ backgroundColor: getAgentColorByName(debate.agent) }">
              <i :class="getAgentIconByName(debate.agent)"></i>
            </div>
            <span class="agent-name">{{ debate.agent }}</span>
          </div>
          <div class="debate-content">
            <p>{{ debate.opinion }}</p>
            <div class="debate-meta">
              <span class="debate-time">{{ formatTime(debate.timestamp) }}</span>
              <span class="debate-confidence">
                {{ $t('analysis.confidence') }}: {{ (debate.confidence * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 共识形成 -->
    <div v-if="consensusReached" class="consensus-section">
      <div class="consensus-header">
        <h4 class="text-lg font-semibold">
          <i class="fas fa-handshake mr-2"></i>
          共识结果
        </h4>
      </div>
      
      <div class="consensus-content">
        <div class="consensus-rating">
          <span class="rating-label">综合评级:</span>
          <span :class="getRatingClass(consensus.rating)" class="rating-value">
            {{ consensus.rating }}
          </span>
        </div>
        
        <div class="consensus-confidence">
          <span class="confidence-label">{{ $t('analysis.confidence') }}:</span>
          <span class="confidence-value">
            {{ (consensus.averageConfidence * 100).toFixed(1) }}%
          </span>
        </div>
        
        <div class="key-findings">
          <h5>关键发现:</h5>
          <ul>
            <li v-for="finding in consensus.keyFindings" :key="finding">
              {{ finding }}
            </li>
          </ul>
        </div>
        
        <div class="recommendations">
          <h5>投资建议:</h5>
          <ul>
            <li v-for="rec in consensus.recommendations" :key="rec">
              {{ rec }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import type { AgentStatus } from '@/types/analysis'

interface Props {
  taskId: string
  symbol: string
}

const props = defineProps<Props>()

// 协作阶段
const phases = ref([
  {
    name: '数据收集',
    description: '获取市场数据和基础信息',
    icon: 'fas fa-database'
  },
  {
    name: '独立分析',
    description: '各分析师独立进行专业分析',
    icon: 'fas fa-search'
  },
  {
    name: '观点辩论',
    description: '分析师交流观点并进行辩论',
    icon: 'fas fa-comments'
  },
  {
    name: '共识形成',
    description: '整合观点形成最终结论',
    icon: 'fas fa-handshake'
  }
])

// 当前阶段
const currentPhase = ref(0)

// 分析师状态
const agents = ref<AgentStatus[]>([
  {
    id: 'technical',
    name: '技术分析师',
    type: 'technical',
    role: '专注于价格趋势和技术指标',
    status: 'idle',
    progress: 0,
    currentTask: '待命中...',
    thoughts: [],
    confidence: 0.5,
    avatar: '📊',
    lastUpdate: new Date().toISOString()
  },
  {
    id: 'fundamental',
    name: '基本面分析师',
    type: 'fundamental',
    role: '关注公司财务和业务模式',
    status: 'idle',
    progress: 0,
    currentTask: '待命中...',
    thoughts: [],
    confidence: 0.5,
    avatar: '💼',
    lastUpdate: new Date().toISOString()
  },
  {
    id: 'sentiment',
    name: '情绪分析师',
    type: 'sentiment',
    role: '分析市场情绪和新闻影响',
    status: 'idle',
    progress: 0,
    currentTask: '待命中...',
    thoughts: [],
    confidence: 0.5,
    avatar: '📈',
    lastUpdate: new Date().toISOString()
  },
  {
    id: 'risk',
    name: '风险分析师',
    type: 'risk',
    role: '评估投资风险和下行保护',
    status: 'idle',
    progress: 0,
    currentTask: '待命中...',
    thoughts: [],
    confidence: 0.5,
    avatar: '⚠️',
    lastUpdate: new Date().toISOString()
  }
])

// 辩论相关状态
const debateActive = ref(false)
const currentDebateTopic = ref('')
const debates = ref<Array<{
  agent: string
  opinion: string
  confidence: number
  timestamp: string
}>>([])

// 共识相关状态
const consensusReached = ref(false)
const consensus = ref({
  rating: 'neutral',
  averageConfidence: 0.5,
  keyFindings: [] as string[],
  recommendations: [] as string[]
})

// WebSocket连接
let ws: WebSocket | null = null

// 计算属性
const statusClass = computed(() => {
  // const phase = phases.value[currentPhase.value] // 未使用的变量
  return {
    'text-blue-600': currentPhase.value < 2,
    'text-yellow-600': currentPhase.value === 2,
    'text-green-600': currentPhase.value === 3
  }
})

const statusText = computed(() => {
  return phases.value[currentPhase.value]?.name || '等待中'
})

// 方法
const phaseClass = (index: number) => {
  return {
    'active': index === currentPhase.value,
    'completed': index < currentPhase.value,
    'pending': index > currentPhase.value
  }
}

const agentStatusClass = (status: string) => {
  return {
    'agent-idle': status === 'idle',
    'agent-thinking': status === 'thinking',
    'agent-analyzing': status === 'analyzing',
    'agent-debating': status === 'debating',
    'agent-completed': status === 'completed',
    'agent-failed': status === 'failed'
  }
}

const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    'idle': 'bg-gray-100 text-gray-800',
    'thinking': 'bg-blue-100 text-blue-800',
    'analyzing': 'bg-yellow-100 text-yellow-800',
    'debating': 'bg-purple-100 text-purple-800',
    'completed': 'bg-green-100 text-green-800',
    'failed': 'bg-red-100 text-red-800'
  }
  return `px-2 py-1 rounded-full text-xs font-medium ${classes[status] || classes.idle}`
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'idle': '待命',
    'thinking': '思考中',
    'analyzing': '分析中',
    'debating': '辩论中',
    'completed': '完成',
    'failed': '失败'
  }
  return texts[status] || '未知'
}

const getConfidenceClass = (confidence: number) => {
  if (confidence >= 0.8) return 'text-green-600 font-bold'
  if (confidence >= 0.6) return 'text-yellow-600 font-medium'
  return 'text-red-600'
}

const getRatingClass = (rating: string) => {
  const classes: Record<string, string> = {
    'bullish': 'text-green-600 font-bold',
    'bearish': 'text-red-600 font-bold',
    'neutral': 'text-gray-600 font-medium'
  }
  return classes[rating] || classes.neutral
}

const getAgentColor = (type: string): string => {
  const colors: Record<string, string> = {
    technical: '#3B82F6',
    fundamental: '#8B5CF6',
    sentiment: '#EC4899',
    risk: '#F59E0B'
  }
  return colors[type] || '#6B7280'
}

const getAgentIcon = (type: string): string => {
  const icons: Record<string, string> = {
    technical: 'fas fa-chart-line',
    fundamental: 'fas fa-coins',
    sentiment: 'fas fa-smile',
    risk: 'fas fa-shield-alt'
  }
  return icons[type] || 'fas fa-user'
}

const getAgentColorByName = (agentName: string): string => {
  const agent = agents.value.find(a => a.name === agentName)
  return agent ? getAgentColor(agent.type) : '#6B7280'
}

const getAgentIconByName = (agentName: string): string => {
  const agent = agents.value.find(a => a.name === agentName)
  return agent ? getAgentIcon(agent.type) : 'fas fa-user'
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString()
}

// WebSocket处理
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_API_BASE_URL?.replace(/^https?:\/\//, '') || window.location.host
  
  ws = new WebSocket(`${protocol}//${host}/api/v1/analysis/ws/${props.taskId}`)
  
  ws.onopen = () => {
    console.log('Agent collaboration WebSocket connected')
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleWebSocketMessage(data)
  }
  
  ws.onclose = () => {
    console.log('Agent collaboration WebSocket disconnected')
    // 重连逻辑
    setTimeout(connectWebSocket, 3000)
  }
  
  ws.onerror = (error) => {
    console.error('Agent collaboration WebSocket error:', error)
  }
}

const handleWebSocketMessage = (data: any) => {
  switch (data.type) {
    case 'phase_update':
      currentPhase.value = data.phase
      break
      
    case 'agent_update':
      updateAgent(data.agent)
      break
      
    case 'debate_start':
      debateActive.value = true
      currentDebateTopic.value = data.topic
      debates.value = []
      break
      
    case 'debate_opinion':
      debates.value.push({
        agent: data.agent,
        opinion: data.opinion,
        confidence: data.confidence,
        timestamp: new Date().toISOString()
      })
      break
      
    case 'consensus_reached':
      consensusReached.value = true
      consensus.value = data.consensus
      debateActive.value = false
      break
  }
}

const updateAgent = (agentData: any) => {
  const index = agents.value.findIndex(a => a.id === agentData.id)
  if (index !== -1) {
    agents.value[index] = { ...agents.value[index], ...agentData }
  }
}

// 模拟分析流程
const startSimulation = () => {
  // 阶段1：数据收集
  currentPhase.value = 0
  agents.value.forEach(agent => {
    agent.status = 'thinking'
    agent.currentTask = '收集市场数据...'
    agent.progress = 0
  })
  
  // 模拟数据收集进度
  let progress = 0
  const dataInterval = setInterval(() => {
    progress += 10
    agents.value.forEach(agent => {
      agent.progress = Math.min(progress + Math.random() * 10, 100)
    })
    
    if (progress >= 100) {
      clearInterval(dataInterval)
      // 进入独立分析阶段
      setTimeout(() => startIndependentAnalysis(), 1000)
    }
  }, 500)
}

const startIndependentAnalysis = () => {
  currentPhase.value = 1
  agents.value.forEach((agent, index) => {
    agent.status = 'analyzing'
    agent.progress = 0
    
    // 设置不同的分析任务
    const tasks: Record<string, string> = {
      technical: '分析K线图和技术指标...',
      fundamental: '评估公司财务数据...',
      sentiment: '分析市场情绪和新闻...',
      risk: '计算风险指标...'
    }
    agent.currentTask = tasks[agent.type] || '分析中...'
    
    // 添加一些思考过程
    setTimeout(() => {
      agent.thoughts.push(`正在分析${props.symbol}的历史数据`)
    }, 1000 + index * 500)
  })
  
  // 模拟分析进度
  let progress = 0
  const analysisInterval = setInterval(() => {
    progress += 5
    agents.value.forEach((agent) => {
      agent.progress = Math.min(progress + Math.random() * 10, 100)
      agent.confidence = 0.5 + (agent.progress / 100) * 0.3 + Math.random() * 0.2
      
      // 随机添加思考
      if (Math.random() > 0.7 && agent.thoughts.length < 5) {
        const thoughts: Record<string, string[]> = {
          technical: [`发现关键支撑位`, `趋势线显示上升通道`, `MACD出现金叉信号`],
          fundamental: [`营收增长稳定`, `利润率有所提升`, `现金流状况良好`],
          sentiment: [`市场情绪偏乐观`, `社交媒体讨论度上升`, `新闻面偏正面`],
          risk: [`波动率处于合理区间`, `系统性风险较低`, `流动性充足`]
        }
        const agentThoughts = thoughts[agent.type] || [`正在深入分析...`]
        agent.thoughts.push(agentThoughts[Math.floor(Math.random() * agentThoughts.length)])
      }
    })
    
    if (progress >= 100) {
      clearInterval(analysisInterval)
      // 进入辩论阶段
      setTimeout(() => startDebate(), 2000)
    }
  }, 800)
}

const startDebate = () => {
  currentPhase.value = 2
  debateActive.value = true
  currentDebateTopic.value = `${props.symbol}的投资价值`
  debates.value = []
  
  agents.value.forEach(agent => {
    agent.status = 'debating'
  })
  
  // 模拟辩论过程
  const debateOpinions = [
    { agent: '技术分析师', opinion: '从技术指标看，该标的处于上升趋势，建议买入', confidence: 0.75 },
    { agent: '基本面分析师', opinion: '公司基本面稳健，但估值偏高，建议谨慎', confidence: 0.65 },
    { agent: '情绪分析师', opinion: '市场情绪积极，短期有上涨动力', confidence: 0.7 },
    { agent: '风险分析师', opinion: '当前风险可控，但需注意市场波动', confidence: 0.6 },
    { agent: '技术分析师', opinion: '关键阻力位即将突破，上涨空间打开', confidence: 0.8 },
    { agent: '基本面分析师', opinion: '考虑到行业前景，长期仍有投资价值', confidence: 0.7 }
  ]
  
  let debateIndex = 0
  const debateInterval = setInterval(() => {
    if (debateIndex < debateOpinions.length) {
      debates.value.push({
        ...debateOpinions[debateIndex],
        timestamp: new Date().toISOString()
      })
      debateIndex++
    } else {
      clearInterval(debateInterval)
      // 形成共识
      setTimeout(() => reachConsensus(), 2000)
    }
  }, 1500)
}

const reachConsensus = () => {
  currentPhase.value = 3
  debateActive.value = false
  consensusReached.value = true
  
  agents.value.forEach(agent => {
    agent.status = 'completed'
    agent.progress = 100
  })
  
  // 计算综合评级
  const avgConfidence = agents.value.reduce((sum, agent) => sum + agent.confidence, 0) / agents.value.length
  const rating = avgConfidence > 0.7 ? 'bullish' : avgConfidence > 0.5 ? 'neutral' : 'bearish'
  
  consensus.value = {
    rating,
    averageConfidence: avgConfidence,
    keyFindings: [
      '技术面显示积极信号',
      '基本面支撑长期增长',
      '市场情绪偏向乐观',
      '风险处于可控范围'
    ],
    recommendations: [
      rating === 'bullish' ? '建议逢低买入' : '建议观望等待',
      '设置止损位以控制风险',
      '关注关键技术位和消息面',
      '分批建仓降低成本'
    ]
  }
}

// 重置状态
const resetAnalysis = () => {
  currentPhase.value = 0
  debateActive.value = false
  consensusReached.value = false
  debates.value = []
  consensus.value = {
    rating: 'neutral',
    averageConfidence: 0.5,
    keyFindings: [],
    recommendations: []
  }
  
  agents.value.forEach(agent => {
    agent.status = 'idle'
    agent.progress = 0
    agent.currentTask = '待命中...'
    agent.thoughts = []
    agent.confidence = 0.5
  })
}

// 监听taskId变化
watch(() => props.taskId, (newTaskId, oldTaskId) => {
  if (newTaskId !== oldTaskId) {
    resetAnalysis()
    
    // 如果是演示模式，重新开始模拟
    if (window.location.hostname === 'localhost' && window.location.port !== '8000') {
      setTimeout(() => startSimulation(), 1000)
    }
  }
})

// 生命周期
onMounted(() => {
  // 尝试连接WebSocket
  connectWebSocket()
  
  // 如果是演示模式，自动开始模拟
  if (window.location.hostname === 'localhost' && window.location.port !== '8000') {
    setTimeout(() => startSimulation(), 1000)
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.agent-collaboration {
  @apply bg-white rounded-lg shadow-sm border p-6;
}

.collaboration-header {
  @apply flex justify-between items-center mb-6;
}

.collaboration-phases {
  @apply flex space-x-4 mb-6;
}

.phase-indicator {
  @apply flex items-center space-x-3 p-3 rounded-lg border-2 transition-all duration-300;
}

.phase-indicator.pending {
  @apply border-gray-200 bg-gray-50 text-gray-400;
}

.phase-indicator.active {
  @apply border-blue-400 bg-blue-50 text-blue-700;
}

.phase-indicator.completed {
  @apply border-green-400 bg-green-50 text-green-700;
}

.phase-icon {
  @apply w-8 h-8 flex items-center justify-center rounded-full;
}

.phase-indicator.pending .phase-icon {
  @apply bg-gray-200;
}

.phase-indicator.active .phase-icon {
  @apply bg-blue-200;
}

.phase-indicator.completed .phase-icon {
  @apply bg-green-200;
}

.agents-panel .agent-card {
  @apply bg-white border rounded-lg p-4 transition-all duration-300;
}

.agent-card.agent-idle {
  @apply border-gray-200;
}

.agent-card.agent-thinking {
  @apply border-blue-300 shadow-md;
}

.agent-card.agent-analyzing {
  @apply border-yellow-300 shadow-md;
}

.agent-card.agent-debating {
  @apply border-purple-300 shadow-lg;
}

.agent-card.agent-completed {
  @apply border-green-300 shadow-sm;
}

.agent-card.agent-failed {
  @apply border-red-300 shadow-sm;
}

.agent-header {
  @apply flex items-center space-x-3 mb-3;
}

.agent-avatar {
  @apply w-10 h-10 rounded-full flex items-center justify-center text-white;
}

.agent-avatar i {
  @apply text-lg;
}

.agent-info .agent-name {
  @apply font-semibold text-gray-900;
}

.agent-info .agent-role {
  @apply text-sm text-gray-600;
}

.agent-progress {
  @apply flex items-center space-x-2 mb-3;
}

.progress-bar {
  @apply flex-1 bg-gray-200 rounded-full h-2;
}

.progress-fill {
  @apply bg-blue-500 h-full rounded-full transition-all duration-300;
}

.agent-current-task .task-text {
  @apply text-sm text-gray-700 italic mb-3;
}

.agent-confidence {
  @apply flex justify-between items-center mb-3;
}

.agent-thoughts {
  @apply border-t pt-3;
}

.thoughts-header {
  @apply flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2;
}

.thoughts-list .thought-item {
  @apply text-xs text-gray-600 p-2 bg-gray-50 rounded mb-1;
}

.debate-section {
  @apply bg-gray-50 rounded-lg p-4 mb-6;
}

.debate-timeline .debate-item {
  @apply flex space-x-3 mb-4 p-3 bg-white rounded-lg;
}

.debate-agent {
  @apply flex items-center space-x-2;
}

.debate-agent-avatar {
  @apply w-8 h-8 rounded-full flex items-center justify-center text-white;
}

.debate-agent-avatar i {
  @apply text-sm;
}

.debate-content {
  @apply flex-1;
}

.debate-meta {
  @apply flex space-x-4 text-xs text-gray-500 mt-2;
}

.consensus-section {
  @apply bg-green-50 rounded-lg p-4;
}

.consensus-content > div {
  @apply mb-3;
}

.consensus-content h5 {
  @apply font-semibold text-gray-800 mb-2;
}

.consensus-content ul {
  @apply list-disc list-inside text-sm text-gray-700;
}
</style>