import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  TaskItem, 
  TaskQueue, 
  TaskStatus, 
  TaskPriority, 
  TaskType,
  ResourceStatus, 
  ResourceType,
  QueueStatistics, 
  BatchOperation, 
  QueueConfig,
  TaskEvent,
  TaskDependency
} from '../types/queue'

export const useQueueStore = defineStore('queue', () => {
  // 队列状态
  const currentQueue = ref<TaskQueue>({
    id: 'main-queue',
    name: '主分析队列',
    description: '主要的分析任务队列',
    tasks: [],
    maxConcurrentTasks: 3,
    currentRunningTasks: 0,
    totalTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  })

  // 资源状态
  const resources = ref<ResourceStatus[]>([
    {
      type: 'analyst',
      id: 'analyst_001',
      name: '技术分析师',
      status: 'idle',
      workload: 0,
      efficiency: 95,
      lastActivity: new Date().toISOString(),
      capabilities: ['技术分析', '图表分析', '趋势识别'],
      maxConcurrentTasks: 2,
      currentTasks: []
    },
    {
      type: 'researcher',
      id: 'researcher_001',
      name: '市场研究员',
      status: 'idle',
      workload: 0,
      efficiency: 92,
      lastActivity: new Date().toISOString(),
      capabilities: ['数据收集', '新闻分析', '市场调研'],
      maxConcurrentTasks: 3,
      currentTasks: []
    },
    {
      type: 'risk_manager',
      id: 'risk_manager_001',
      name: '风险管理师',
      status: 'idle',
      workload: 0,
      efficiency: 97,
      lastActivity: new Date().toISOString(),
      capabilities: ['风险评估', '压力测试', '合规检查'],
      maxConcurrentTasks: 2,
      currentTasks: []
    },
    {
      type: 'strategist',
      id: 'strategist_001',
      name: '投资策略师',
      status: 'idle',
      workload: 0,
      efficiency: 94,
      lastActivity: new Date().toISOString(),
      capabilities: ['策略制定', '资产配置', '投资建议'],
      maxConcurrentTasks: 1,
      currentTasks: []
    }
  ])

  // 队列配置
  const queueConfig = ref<QueueConfig>({
    maxConcurrentTasks: 3,
    defaultPriority: 'normal',
    autoRetry: true,
    maxRetries: 3,
    retryDelay: 60,
    timeoutDuration: 3600,
    enableDependencies: true,
    resourceAllocation: 'automatic'
  })

  // 任务事件历史
  const taskEvents = ref<TaskEvent[]>([])

  // 计算属性
  const queueStatistics = computed<QueueStatistics>(() => {
    const tasks = currentQueue.value.tasks
    const completedTasks = tasks.filter(t => t.status === 'completed')
    const failedTasks = tasks.filter(t => t.status === 'failed')
    
    return {
      totalTasks: tasks.length,
      pendingTasks: tasks.filter(t => t.status === 'pending' || t.status === 'queued').length,
      runningTasks: tasks.filter(t => t.status === 'running').length,
      completedTasks: completedTasks.length,
      failedTasks: failedTasks.length,
      averageWaitTime: calculateAverageWaitTime(),
      averageExecutionTime: calculateAverageExecutionTime(),
      throughput: calculateThroughput(),
      successRate: tasks.length > 0 ? (completedTasks.length / tasks.length) * 100 : 0,
      resourceUtilization: calculateResourceUtilization()
    }
  })

  const runningTasks = computed(() => 
    currentQueue.value.tasks.filter(task => task.status === 'running')
  )

  const pendingTasks = computed(() => 
    currentQueue.value.tasks.filter(task => task.status === 'pending' || task.status === 'queued')
  )

  const availableResources = computed(() => 
    resources.value.filter(resource => resource.status === 'idle')
  )

  // Actions
  const addTask = (taskData: Omit<TaskItem, 'id' | 'createdAt' | 'updatedAt' | 'progress'>) => {
    const task: TaskItem = {
      ...taskData,
      id: generateTaskId(),
      progress: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    currentQueue.value.tasks.push(task)
    currentQueue.value.totalTasks++
    currentQueue.value.updatedAt = new Date().toISOString()

    // 记录事件
    addTaskEvent(task.id, 'created', `任务创建: ${task.name}`)

    // 如果满足条件，自动启动任务
    tryAutoStartTasks()

    return task.id
  }

  const updateTaskStatus = (taskId: string, status: TaskStatus, progress?: number) => {
    const task = currentQueue.value.tasks.find(t => t.id === taskId)
    if (!task) return

    const oldStatus = task.status
    task.status = status
    task.updatedAt = new Date().toISOString()

    if (progress !== undefined) {
      task.progress = progress
    }

    // 更新时间戳
    if (status === 'running' && oldStatus !== 'running') {
      task.startedAt = new Date().toISOString()
      currentQueue.value.currentRunningTasks++
    } else if (status === 'completed') {
      task.completedAt = new Date().toISOString()
      task.progress = 100
      if (task.startedAt) {
        task.actualDuration = Math.floor((new Date().getTime() - new Date(task.startedAt).getTime()) / 1000)
      }
      currentQueue.value.completedTasks++
      if (oldStatus === 'running') {
        currentQueue.value.currentRunningTasks--
      }
      releaseTaskResources(taskId)
    } else if (status === 'failed') {
      task.completedAt = new Date().toISOString()
      currentQueue.value.failedTasks++
      if (oldStatus === 'running') {
        currentQueue.value.currentRunningTasks--
      }
      releaseTaskResources(taskId)
    } else if (status === 'cancelled') {
      if (oldStatus === 'running') {
        currentQueue.value.currentRunningTasks--
      }
      releaseTaskResources(taskId)
    }

    // 记录事件
    addTaskEvent(taskId, status, `任务状态变更: ${oldStatus} -> ${status}`)

    // 尝试启动等待中的任务
    tryAutoStartTasks()
  }

  const updateTaskPriority = (taskId: string, priority: TaskPriority) => {
    const task = currentQueue.value.tasks.find(t => t.id === taskId)
    if (!task) return

    task.priority = priority
    task.updatedAt = new Date().toISOString()

    // 重新排序队列
    sortTasksByPriority()

    addTaskEvent(taskId, 'prioritize', `优先级变更为: ${priority}`)
  }

  const deleteTask = (taskId: string) => {
    const taskIndex = currentQueue.value.tasks.findIndex(t => t.id === taskId)
    if (taskIndex === -1) return

    const task = currentQueue.value.tasks[taskIndex]
    
    // 如果是运行中的任务，先停止
    if (task.status === 'running') {
      currentQueue.value.currentRunningTasks--
      releaseTaskResources(taskId)
    }

    currentQueue.value.tasks.splice(taskIndex, 1)
    currentQueue.value.totalTasks--
    currentQueue.value.updatedAt = new Date().toISOString()

    addTaskEvent(taskId, 'cancelled', `任务删除: ${task.name}`)
  }

  const batchOperation = async (operation: BatchOperation) => {
    const { action, taskIds, parameters } = operation

    for (const taskId of taskIds) {
      switch (action) {
        case 'start':
          if (canStartTask(taskId)) {
            updateTaskStatus(taskId, 'running')
          }
          break
        case 'pause':
          updateTaskStatus(taskId, 'paused')
          break
        case 'cancel':
          updateTaskStatus(taskId, 'cancelled')
          break
        case 'delete':
          deleteTask(taskId)
          break
        case 'prioritize':
          if (parameters?.priority) {
            updateTaskPriority(taskId, parameters.priority)
          }
          break
      }
    }

    addTaskEvent('batch', action, `批量操作: ${action} - ${taskIds.length} 个任务`)
  }

  const getTaskDependencies = (taskId: string): TaskDependency => {
    const task = currentQueue.value.tasks.find(t => t.id === taskId)
    if (!task) {
      return {
        taskId,
        dependsOn: [],
        blockedBy: [],
        canStart: false,
        waitingFor: []
      }
    }

    const dependsOn = task.dependencies
    const blockedBy = currentQueue.value.tasks
      .filter(t => t.dependencies.includes(taskId))
      .map(t => t.id)

    const waitingFor = dependsOn.filter(depId => {
      const depTask = currentQueue.value.tasks.find(t => t.id === depId)
      return depTask && depTask.status !== 'completed'
    })

    return {
      taskId,
      dependsOn,
      blockedBy,
      canStart: waitingFor.length === 0,
      waitingFor
    }
  }

  // 辅助函数
  const generateTaskId = (): string => {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const addTaskEvent = (taskId: string, type: TaskEvent['type'], message: string) => {
    const event: TaskEvent = {
      id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      taskId,
      type,
      timestamp: new Date().toISOString(),
      message
    }
    taskEvents.value.unshift(event)

    // 保留最近1000条事件
    if (taskEvents.value.length > 1000) {
      taskEvents.value = taskEvents.value.slice(0, 1000)
    }
  }

  const canStartTask = (taskId: string): boolean => {
    const task = currentQueue.value.tasks.find(t => t.id === taskId)
    if (!task || task.status === 'running') return false

    // 检查并发限制
    if (currentQueue.value.currentRunningTasks >= queueConfig.value.maxConcurrentTasks) {
      return false
    }

    // 检查依赖关系
    const dependencies = getTaskDependencies(taskId)
    if (!dependencies.canStart) return false

    // 检查资源可用性
    const requiredResources = task.assignedResources
    const hasAvailableResources = requiredResources.every(resourceType => {
      const resource = resources.value.find(r => r.type === resourceType && r.status === 'idle')
      return resource && resource.currentTasks.length < resource.maxConcurrentTasks
    })

    return hasAvailableResources
  }

  const tryAutoStartTasks = () => {
    if (queueConfig.value.resourceAllocation !== 'automatic') return

    const pendingTasks = currentQueue.value.tasks
      .filter(task => task.status === 'pending' || task.status === 'queued')
      .sort((a, b) => getPriorityWeight(b.priority) - getPriorityWeight(a.priority))

    for (const task of pendingTasks) {
      if (canStartTask(task.id)) {
        allocateTaskResources(task.id)
        updateTaskStatus(task.id, 'running')
      }
    }
  }

  const allocateTaskResources = (taskId: string) => {
    const task = currentQueue.value.tasks.find(t => t.id === taskId)
    if (!task) return

    for (const resourceType of task.assignedResources) {
      const resource = resources.value.find(r => 
        r.type === resourceType && 
        r.currentTasks.length < r.maxConcurrentTasks
      )
      if (resource) {
        resource.currentTasks.push(taskId)
        resource.status = 'busy'
        resource.lastActivity = new Date().toISOString()
        updateResourceWorkload(resource.id)
      }
    }
  }

  const releaseTaskResources = (taskId: string) => {
    for (const resource of resources.value) {
      const taskIndex = resource.currentTasks.indexOf(taskId)
      if (taskIndex !== -1) {
        resource.currentTasks.splice(taskIndex, 1)
        resource.lastActivity = new Date().toISOString()
        
        if (resource.currentTasks.length === 0) {
          resource.status = 'idle'
        }
        
        updateResourceWorkload(resource.id)
      }
    }
  }

  const updateResourceWorkload = (resourceId: string) => {
    const resource = resources.value.find(r => r.id === resourceId)
    if (!resource) return

    resource.workload = (resource.currentTasks.length / resource.maxConcurrentTasks) * 100
  }

  const sortTasksByPriority = () => {
    currentQueue.value.tasks.sort((a, b) => {
      // 首先按状态排序（运行中的在前）
      const statusWeight = { running: 4, paused: 3, queued: 2, pending: 1, completed: 0, failed: 0, cancelled: 0 }
      const statusDiff = (statusWeight[b.status] || 0) - (statusWeight[a.status] || 0)
      if (statusDiff !== 0) return statusDiff

      // 然后按优先级排序
      return getPriorityWeight(b.priority) - getPriorityWeight(a.priority)
    })
  }

  const getPriorityWeight = (priority: TaskPriority): number => {
    const weights = { urgent: 4, high: 3, normal: 2, low: 1 }
    return weights[priority] || 2
  }

  const calculateAverageWaitTime = (): number => {
    const completedTasks = currentQueue.value.tasks.filter(t => t.status === 'completed' && t.startedAt)
    if (completedTasks.length === 0) return 0

    const totalWaitTime = completedTasks.reduce((sum, task) => {
      const waitTime = new Date(task.startedAt!).getTime() - new Date(task.createdAt).getTime()
      return sum + waitTime
    }, 0)

    return Math.floor(totalWaitTime / completedTasks.length / 1000) // 转换为秒
  }

  const calculateAverageExecutionTime = (): number => {
    const completedTasks = currentQueue.value.tasks.filter(t => t.actualDuration)
    if (completedTasks.length === 0) return 0

    const totalExecutionTime = completedTasks.reduce((sum, task) => sum + (task.actualDuration || 0), 0)
    return Math.floor(totalExecutionTime / completedTasks.length)
  }

  const calculateThroughput = (): number => {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000)
    const recentCompletedTasks = currentQueue.value.tasks.filter(task => 
      task.status === 'completed' && 
      task.completedAt && 
      new Date(task.completedAt) > oneHourAgo
    )
    return recentCompletedTasks.length
  }

  const calculateResourceUtilization = (): number => {
    const totalCapacity = resources.value.reduce((sum, resource) => sum + resource.maxConcurrentTasks, 0)
    const usedCapacity = resources.value.reduce((sum, resource) => sum + resource.currentTasks.length, 0)
    return totalCapacity > 0 ? (usedCapacity / totalCapacity) * 100 : 0
  }

  // 生成模拟数据（仅开发模式）
  const generateMockTasks = () => {
    // 仅在开发模式下生成模拟数据
    if (import.meta.env.VITE_USE_MOCK_DATA !== 'true') {
      console.warn('Mock tasks generation is only available in development mode')
      return
    }
    
    const symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AAPL', 'TSLA', 'MSFT']
    const priorities: TaskPriority[] = ['low', 'normal', 'high', 'urgent']
    const statuses: TaskStatus[] = ['pending', 'queued', 'running', 'completed', 'failed']

    for (let i = 0; i < 8; i++) {
      const symbol = symbols[Math.floor(Math.random() * symbols.length)]
      const priority = priorities[Math.floor(Math.random() * priorities.length)]
      const status = statuses[Math.floor(Math.random() * statuses.length)]
      
      addTask({
        name: `${symbol} 深度分析`,
        type: 'analysis',
        status: 'pending',
        priority,
        config: {
          symbol,
          timeframe: '1h',
          depth: 3,
          analysts: ['technical_analyst', 'fundamental_analyst'],
          llmProvider: 'openai',
          llmModel: 'gpt-4o-mini'
        },
        estimatedDuration: Math.floor(Math.random() * 1800) + 300, // 5-35分钟
        dependencies: [],
        assignedResources: ['analyst', 'researcher']
      })

      // 模拟更新一些任务状态
      const tasks = currentQueue.value.tasks
      if (tasks.length > 0) {
        const randomTask = tasks[Math.floor(Math.random() * tasks.length)]
        updateTaskStatus(randomTask.id, status, Math.floor(Math.random() * 100))
      }
    }
  }

  return {
    // State
    currentQueue,
    resources,
    queueConfig,
    taskEvents,
    
    // Computed
    queueStatistics,
    runningTasks,
    pendingTasks,
    availableResources,
    
    // Actions
    addTask,
    updateTaskStatus,
    updateTaskPriority,
    deleteTask,
    batchOperation,
    getTaskDependencies,
    canStartTask,
    tryAutoStartTasks,
    generateMockTasks
  }
}) 