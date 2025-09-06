/**
 * 智能体协作系统类型定义
 * Multi-Agent Collaboration System Type Definitions
 */

// 智能体状态枚举
export type AgentStatus = 'idle' | 'thinking' | 'working' | 'communicating' | 'completed' | 'error'

// 智能体类型枚举
export type AgentType = 'analyst' | 'researcher' | 'risk_manager' | 'strategist'

// 协作阶段枚举
export type CollaborationStage = 
  | 'initialization' 
  | 'data_gathering' 
  | 'analysis' 
  | 'cross_validation' 
  | 'synthesis' 
  | 'recommendation'

// 交互类型枚举
export type InteractionType = 
  | 'data_request' 
  | 'analysis_sharing' 
  | 'validation_request' 
  | 'consensus_building' 
  | 'result_compilation'

// 智能体基础信息
export interface AgentInfo {
  id: string
  type: AgentType
  name: string
  description: string
  capabilities: string[]
  avatar?: string
  color: string
}

// 智能体实时状态
export interface AgentState {
  agentId: string
  status: AgentStatus
  currentTask?: string
  progress: number // 0-100
  lastActivity: string
  estimatedCompletion?: string
  errorMessage?: string
}

// 智能体消息
export interface AgentMessage {
  id: string
  fromAgent: string
  toAgent?: string // undefined表示广播消息
  type: InteractionType
  content: string
  data?: Record<string, any>
  timestamp: string
  isRead: boolean
}

// 协作任务
export interface CollaborationTask {
  id: string
  title: string
  description: string
  symbol?: string
  parameters: Record<string, any>
  requiredAgents: AgentType[]
  currentStage: CollaborationStage
  startTime: string
  estimatedDuration: number // 分钟
  completedTime?: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
}

// 协作流程节点
export interface CollaborationNode {
  id: string
  stage: CollaborationStage
  title: string
  description: string
  involvedAgents: string[]
  status: 'pending' | 'active' | 'completed' | 'skipped'
  startTime?: string
  endTime?: string
  duration?: number
  outputs?: Record<string, any>
}

// 协作流程
export interface CollaborationFlow {
  taskId: string
  nodes: CollaborationNode[]
  connections: {
    from: string
    to: string
    condition?: string
  }[]
  currentNode?: string
  progress: number
}

// 智能体性能指标
export interface AgentPerformance {
  agentId: string
  taskCount: number
  completionRate: number
  averageQuality: number
  collaborationScore: number
  efficiency: number
  responseTime: number // 平均响应时间(秒)
  lastEvaluated: string
}

// 协作绩效
export interface CollaborationPerformance {
  taskId: string
  overallScore: number
  efficiency: number
  accuracy: number
  consensusLevel: number
  completionTime: number
  qualityScore: number
  agentPerformances: AgentPerformance[]
}

// 实时协作状态
export interface CollaborationState {
  task: CollaborationTask
  agents: AgentState[]
  flow: CollaborationFlow
  messages: AgentMessage[]
  performance?: CollaborationPerformance
  isActive: boolean
  lastUpdated: string
}

// 协作历史记录
export interface CollaborationHistory {
  id: string
  task: CollaborationTask
  finalPerformance: CollaborationPerformance
  summary: string
  keyInsights: string[]
  recommendations: string[]
  createdAt: string
}

// WebSocket消息类型
export interface AgentWebSocketMessage {
  type: 'agent_status_update' | 'new_message' | 'task_progress' | 'collaboration_complete'
  data: AgentState | AgentMessage | CollaborationFlow | CollaborationPerformance
}

// 协作配置
export interface CollaborationConfig {
  maxConcurrentTasks: number
  defaultTimeout: number // 分钟
  enableAutoRetry: boolean
  retryAttempts: number
  consensusThreshold: number // 0-1
  qualityThreshold: number // 0-1
}

// 协作分析结果
export interface CollaborationAnalysis {
  taskId: string
  symbol?: string
  findings: {
    agentId: string
    analysis: Record<string, any>
    confidence: number
    timestamp: string
  }[]
  consensus: {
    points: string[]
    disagreements: string[]
    finalRecommendation: string
    confidenceLevel: number
  }
  risks: {
    identified: string[]
    mitigation: string[]
    severity: 'low' | 'medium' | 'high'
  }[]
  nextSteps: string[]
} 