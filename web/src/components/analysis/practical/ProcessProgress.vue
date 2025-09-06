<template>
  <div class="process-progress">
    <div class="progress-content">
      <!-- 统计信息移到顶部 -->
      <div class="stats-section">
        <div class="stat-item">
          <span class="stat-label">{{ $t('common.progress') }}:</span>
          <span class="stat-value">{{ Math.round(progress) }}%</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ $t('analysis.agents.active') }}:</span>
          <span class="stat-value">{{ activeAgentCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ $t('analysis.status.completed') }}:</span>
          <span class="stat-value">{{ completedTaskCount }}</span>
        </div>
        <div class="stat-item" v-if="progress > 0 && progress < 100">
          <span class="stat-label">{{ $t('common.remaining') }}:</span>
          <span class="stat-value">{{ estimatedTime }}</span>
        </div>
      </div>
      
      <!-- 总进度条 -->
      <div class="overall-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
          <div class="progress-info">
          <span class="current-stage" :title="getCurrentStageName()">{{ getCurrentStageName() }}</span>
          </div>
      </div>
      
      <!-- 动态分析阶段 - 横向布局 -->
      <div class="stages stages-horizontal">
        <div 
          v-for="stage in stageList" 
          :key="stage.key"
          class="stage-block" 
          :class="getStageClass(stage.key)"
        >
          <div class="stage-header">
            <span class="stage-number">{{ stage.number }}</span>
            <span class="stage-name" :title="stage.name">{{ stage.name }}</span>
            <span class="stage-status">{{ getStageStatus(stage.key) }}</span>
          </div>
          <div class="agent-list">
            <div 
              v-for="agent in agents[stage.key]" 
              :key="agent.id"
              class="agent-item"
              :class="agent.status"
            >
              <span class="agent-icon">{{ getAgentIcon(agent.status) }}</span>
              <span class="agent-name" :title="agent.name">{{ agent.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

// 显式定义组件名称以提高 Vetur 兼容性
defineOptions({
  name: 'ProcessProgress'
})

interface Agent {
  id: string
  name: string
  status: 'idle' | 'processing' | 'completed' | 'error'
}

interface Props {
  currentStage: string
  agents: Record<string, Agent[]>
  progress: number
}

const props = defineProps<Props>()
const { t } = useI18n()

// 阶段名称映射
const getStageDisplayName = (stage: string) => {
  const stageNames: Record<string, string> = {
    // 加密市场阶段
    analyst: t('analysis.teams.analyst'),
    research: t('analysis.teams.research'),
    trading: t('analysis.teams.trading'),
    risk: t('analysis.teams.risk'),
    portfolio: t('analysis.teams.portfolio'),
    // 预测市场阶段
    probability: t('analysis.teams.probability'),
    strategy: t('analysis.teams.strategy'),
    decision: t('analysis.teams.decision')
  }
  return stageNames[stage] || stage
}

// 动态生成阶段列表
const stageList = computed(() => {
  // 过滤掉没有agents或agents为空数组的阶段
  const stages = Object.keys(props.agents).filter(key => {
    const agentList = props.agents[key]
    return agentList && Array.isArray(agentList) && agentList.length > 0
  })
  
  // 使用i18n获取阶段编号，支持动态语言切换
  const getStageNumber = (stageKey: string): string => {
    const translationKey = `agents.stageNumbers.${stageKey}`
    const translated = t(translationKey)
    return translated !== translationKey ? translated : 'X'
  }
  
  return stages.map(key => ({
    key,
    name: getStageDisplayName(key),
    number: getStageNumber(key)
  }))
})

// 响应式数据
const startTime = ref(Date.now())
const runningTime = ref('00:00')
const estimatedTime = ref(t('ui.loading.processing'))

// 更新运行时间
const updateRunningTime = () => {
  const elapsed = Date.now() - startTime.value
  const seconds = Math.floor(elapsed / 1000)
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  runningTime.value = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  
  // 估算剩余时间
  if (props.progress > 0 && props.progress < 100) {
    const totalEstimated = (elapsed / props.progress) * 100
    const remaining = totalEstimated - elapsed
    const remainingSeconds = Math.floor(remaining / 1000)
    const remainingMinutes = Math.floor(remainingSeconds / 60)
    const remainingSecs = remainingSeconds % 60
    estimatedTime.value = `${remainingMinutes}:${String(remainingSecs).padStart(2, '0')}`
  }
}

// 监听进度变化
watch(() => props.progress, () => {
  updateRunningTime()
})

// 计算属性
const activeAgentCount = computed(() => {
  let count = 0
  Object.values(props.agents).forEach(group => {
    group.forEach(agent => {
      if (agent.status === 'processing') {
        count++
      }
    })
  })
  return count
})

const completedTaskCount = computed(() => {
  let count = 0
  Object.values(props.agents).forEach(group => {
    group.forEach(agent => {
      if (agent.status === 'completed') {
        count++
      }
    })
  })
  return count
})

// 辅助方法
const getCurrentStageName = () => {
  const stageNames: Record<string, string> = {
    idle: t('analysis.stream.waiting'),
    // 加密市场阶段
    analyst: t('analysis.phases.data'),
    research: t('analysis.phases.research'),
    trading: t('analysis.phases.trading'),
    risk: t('analysis.phases.risk'),
    portfolio: t('analysis.phases.portfolio'),
    // 预测市场阶段
    probability: t('analysis.phases.probability'),
    strategy: t('analysis.phases.strategy'),
    decision: t('analysis.phases.decision')
  }
  return stageNames[props.currentStage] || t('analysis.phases.unknown')
}

const getStageClass = (stage: string) => {
  const stageAgents = props.agents[stage as keyof typeof props.agents]
  const hasRunningAgent = stageAgents?.some(agent => agent.status === 'processing')
  
  return {
    active: props.currentStage === stage,
    completed: isStageCompleted(stage),
    pending: isStagePending(stage),
    'has-running': hasRunningAgent // 有正在运行的Agent
  }
}

const getStageStatus = (stage: string) => {
  if (props.currentStage === stage) return t('analysis.status.running')
  if (isStageCompleted(stage)) return t('analysis.status.completed')
  return t('analysis.status.waiting')
}

const isStageCompleted = (stage: string) => {
  // 动态获取当前的阶段顺序
  const stageOrder = Object.keys(props.agents)
  const currentIndex = stageOrder.indexOf(props.currentStage)
  const stageIndex = stageOrder.indexOf(stage)
  return stageIndex < currentIndex
}

const isStagePending = (stage: string) => {
  // 动态获取当前的阶段顺序
  const stageOrder = Object.keys(props.agents)
  const currentIndex = stageOrder.indexOf(props.currentStage)
  const stageIndex = stageOrder.indexOf(stage)
  return stageIndex > currentIndex
}

const getAgentIcon = (status: string) => {
  const icons: Record<string, string> = {
    idle: '⏸',
    processing: '⚡',
    completed: '✓',
    error: '✗'
  }
  return icons[status] || '•'
}

// 定时更新运行时间
setInterval(updateRunningTime, 1000)
</script>

<style lang="scss" scoped>
.process-progress {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: var(--od-text-primary);
  font-family: 'Proto Mono', monospace;
  font-size: 13px;
  background: var(--od-background);
}

.progress-content {
  flex: 1;
  padding: 0.75rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  
  .overall-progress {
    margin-bottom: 1rem;
    flex-shrink: 0;
    
    .progress-bar {
      height: 16px;
      background: var(--od-background-alt);
      border: 1px solid var(--od-border);
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 0.5rem;
      position: relative;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) inset;
      
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, 
          var(--od-primary) 0%, 
          var(--od-accent) 50%, 
          var(--od-primary) 100%
        );
        background-size: 200% 100%;
        animation: progressGradient 3s ease-in-out infinite;
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        border-radius: 7px;
        box-shadow: 0 0 10px rgba(78, 201, 176, 0.4);
        
        &::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 50%;
          background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.3) 0%,
            transparent 100%
          );
          border-radius: 7px 7px 0 0;
        }
        
        &::after {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 30%;
          height: 100%;
          background: linear-gradient(90deg, 
            transparent 0%, 
            rgba(255, 255, 255, 0.4) 30%,
            rgba(255, 255, 255, 0.7) 50%,
            rgba(255, 255, 255, 0.4) 70%,
            transparent 100%);
          animation: progress-shimmer 2.5s ease-in-out infinite;
          border-radius: 7px;
        }
      }
    }
    
    .progress-info {
      display: flex;
      justify-content: center;
      font-size: 13px;
      font-weight: 500;
      
      .current-stage {
        color: var(--od-accent);
        text-shadow: 0 0 10px rgba(var(--od-accent-rgb), 0.3);
      }
      
      .eta {
        color: var(--od-text-secondary);
      }
    }
  }
  
  .stages {
    flex: 1;
    min-height: 0;
    
    &.stages-vertical {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      overflow-y: auto;
      padding-right: 0.25rem;
      
      .stage-block {
        flex-shrink: 0;
        min-height: 80px;
      }
    }
    
    &.stages-horizontal {
      display: flex;
      gap: 0.375rem;
      overflow-x: auto;
      overflow-y: hidden;
      padding-bottom: 0.375rem;
      scrollbar-width: thin;
      scrollbar-color: var(--od-border) transparent;
      
      &::-webkit-scrollbar {
        height: 4px;
      }
      
      &::-webkit-scrollbar-track {
        background: transparent;
      }
      
      &::-webkit-scrollbar-thumb {
        background: var(--od-border);
        border-radius: 2px;
        
        &:hover {
          background: var(--od-text-muted);
        }
      }
      
      .stage-block {
        flex: 1;
        min-width: 160px;
        max-width: 200px;
      }
    }
    
    .stage-block {
      padding: 0.375rem;
      background: var(--od-background-alt);
      border: 1px solid var(--od-border);
      border-radius: var(--border-radius-sm);
      transition: all 0.3s;
      display: flex;
      flex-direction: column;
      position: relative;
      
      &.active {
        // 简单的背景变化
        background: var(--od-background);
        
        .stage-header {
          color: var(--od-accent);
        }
      }
      
      // 有Agent正在运行时，保持简单的状态显示
      &.has-running {
        // 不改变边框，只改变内容颜色
        .stage-header {
          .stage-number {
            color: var(--od-primary);
            font-weight: bold;
          }
          
          .stage-name {
            color: var(--od-primary-light);
            font-weight: 600;
          }
          
          .stage-status {
            color: var(--od-primary);
            font-weight: bold;
          }
        }
      }
      
      &.completed {
        opacity: 0.7;
        
        .stage-header {
          color: var(--od-primary);
        }
      }
      
      &.pending {
        opacity: 0.5;
      }
      
      .stage-header {
        display: flex;
        align-items: center;
        margin-bottom: 0.375rem;
        font-weight: bold;
        flex-shrink: 0;
        
        .stage-number {
          margin-right: 0.375rem;
          padding: 0.125rem 0.25rem;
          background: var(--od-background);
          border: 1px solid var(--od-border);
          border-radius: 2px;
          font-size: 9px;
        }
        
        .stage-name {
          flex: 1;
          font-size: 12px;
        }
        
        .stage-status {
          font-size: 10px;
          color: var(--od-text-secondary);
        }
      }
      
      .agent-list {
        display: flex;
        flex-direction: column;
        gap: 0.125rem;
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        
        .agent-item {
          display: flex;
          align-items: center;
          padding: 0.25rem 0.375rem;
          background: var(--od-background);
          border: 1px solid var(--od-border);
          border-radius: 2px;
          font-size: 10px;
          flex-shrink: 0;
          position: relative;
          
          &.processing {
            background: var(--od-background);
            border: 2px solid var(--od-primary);
            border-radius: 4px;
            position: relative;
            animation: border-pulse 2s ease-in-out infinite;
            box-shadow: 0 0 8px rgba(74, 222, 128, 0.3);
            
            .agent-name {
              color: var(--od-primary-light);
              font-weight: 600;
            }
            
            .agent-icon {
              color: var(--od-primary);
              animation: icon-glow 1.5s ease-in-out infinite;
            }
          }
          
          &.completed {
            opacity: 0.6;
          }
          
          &.error {
            background: var(--od-background);
            border-color: var(--od-error);
            color: var(--od-error);
          }
          
          .agent-icon {
            margin-right: 0.25rem;
          }
          
          .agent-name {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
      }
    }
  }
  
  .stats-section {
    margin-bottom: 0.5rem;
    padding: 0.375rem 0.5rem;
    background: var(--od-background-alt);
    border: 1px solid var(--od-border);
    border-radius: var(--border-radius-sm);
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
    
    .stat-item {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      
      .stat-label {
        color: var(--od-text-secondary);
        font-size: 12px;
      }
      
      .stat-value {
        color: var(--od-primary);
        font-size: 14px;
        font-weight: bold;
      }
    }
  }
}

// Agent边框脉冲动画
@keyframes border-pulse {
  0%, 100% {
    border-color: var(--od-primary);
    box-shadow: 0 0 8px rgba(74, 222, 128, 0.3);
  }
  50% {
    border-color: var(--od-primary-light);
    box-shadow: 0 0 16px rgba(74, 222, 128, 0.6);
  }
}

// Agent图标光晕动画
@keyframes icon-glow {
  0%, 100% {
    text-shadow: 0 0 4px var(--od-primary);
  }
  50% {
    text-shadow: 0 0 8px var(--od-primary);
  }
}

// 保留基础动画以备后用
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

// 进度条流光效果
@keyframes progress-shimmer {
  0% {
    left: -30%;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    left: 100%;
    opacity: 0;
  }
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    transform: translateX(100%);
    opacity: 0;
  }
}

@keyframes progressGradient {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}

// 仅为垂直布局的agent列表保留滚动条样式
.agent-list::-webkit-scrollbar {
  width: 4px;
}

.agent-list::-webkit-scrollbar-track {
  background: transparent;
}

.agent-list::-webkit-scrollbar-thumb {
  background: var(--od-border);
  border-radius: 2px;
  
  &:hover {
    background: var(--od-text-muted);
  }
}
</style>
