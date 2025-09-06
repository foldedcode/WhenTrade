/**
 * 任务队列系统类型定义
 * Task Queue System Type Definitions
 */

// 任务状态枚举
export type TaskStatus = 'pending' | 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'

// 任务优先级枚举
export type TaskPriority = 'low' | 'normal' | 'high' | 'urgent'

// 任务类型枚举
export type TaskType = 'analysis' | 'research' | 'risk_assessment' | 'strategy'

// 资源类型枚举
export type ResourceType = 'analyst' | 'researcher' | 'risk_manager' | 'strategist'

// 任务项接口
export interface TaskItem {
  id: string
  name: string
  type: TaskType
  status: TaskStatus
  priority: TaskPriority
  config: {
    symbol: string
    timeframe: string
    depth: number
    analysts: string[]
    llmProvider: string
    llmModel: string
  }
  progress: number
  createdAt: string
  updatedAt: string
  scheduledAt?: string
  startedAt?: string
  completedAt?: string
  estimatedDuration: number // 预估耗时（秒）
  actualDuration?: number // 实际耗时（秒）
  dependencies: string[] // 依赖的任务ID
  assignedResources: ResourceType[]
  cost?: number
  errorMessage?: string
  metadata?: Record<string, any>
}

// 任务队列接口
export interface TaskQueue {
  id: string
  name: string
  description?: string
  tasks: TaskItem[]
  maxConcurrentTasks: number
  currentRunningTasks: number
  totalTasks: number
  completedTasks: number
  failedTasks: number
  createdAt: string
  updatedAt: string
}

// 资源状态接口
export interface ResourceStatus {
  type: ResourceType
  id: string
  name: string
  status: 'idle' | 'busy' | 'overloaded' | 'maintenance'
  currentTask?: string
  workload: number // 0-100
  efficiency: number // 0-100
  lastActivity: string
  capabilities: string[]
  maxConcurrentTasks: number
  currentTasks: string[]
}

// 队列统计接口
export interface QueueStatistics {
  totalTasks: number
  pendingTasks: number
  runningTasks: number
  completedTasks: number
  failedTasks: number
  averageWaitTime: number // 平均等待时间（秒）
  averageExecutionTime: number // 平均执行时间（秒）
  throughput: number // 每小时完成任务数
  successRate: number // 成功率（0-100）
  resourceUtilization: number // 资源利用率（0-100）
}

// 批量操作接口
export interface BatchOperation {
  action: 'start' | 'pause' | 'cancel' | 'delete' | 'prioritize'
  taskIds: string[]
  parameters?: Record<string, any>
}

// 任务依赖关系接口
export interface TaskDependency {
  taskId: string
  dependsOn: string[]
  blockedBy: string[]
  canStart: boolean
  waitingFor: string[]
}

// 队列配置接口
export interface QueueConfig {
  maxConcurrentTasks: number
  defaultPriority: TaskPriority
  autoRetry: boolean
  maxRetries: number
  retryDelay: number // 重试延迟（秒）
  timeoutDuration: number // 超时时间（秒）
  enableDependencies: boolean
  resourceAllocation: 'automatic' | 'manual'
}

// 任务历史记录接口
export interface TaskHistory {
  taskId: string
  action: string
  timestamp: string
  details: string
  userId?: string
}

// 性能指标接口
export interface PerformanceMetrics {
  queueId: string
  timestamp: string
  metrics: {
    waitTime: number
    executionTime: number
    throughput: number
    errorRate: number
    resourceUtilization: Record<ResourceType, number>
  }
}

// 任务事件接口
export interface TaskEvent {
  id: string
  taskId: string
  type: 'created' | 'started' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'pending' | 'queued' | 'running' | 'prioritize' | 'start' | 'pause' | 'cancel' | 'delete'
  timestamp: string
  message: string
  metadata?: Record<string, any>
} 