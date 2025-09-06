// 任务状态
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'

// 任务类型
export type TaskType = 'research' | 'analysis' | 'monitor' | 'alert'

// 创建任务的请求数据
export interface TaskCreate {
  type: TaskType
  config: {
    symbol?: string
    timeframe?: string
    indicators?: string[]
    depth?: number
    analysts?: string[]
    [key: string]: any
  }
  priority?: 'low' | 'medium' | 'high'
  scheduled_at?: string
}

// 任务响应数据
export interface TaskResponse {
  id: string
  user_id: string
  type: TaskType
  status: TaskStatus
  config: Record<string, any>
  result?: Record<string, any>
  error?: string
  progress: number
  priority: string
  created_at: string
  started_at?: string
  completed_at?: string
  scheduled_at?: string
}

// 报告类型
export type ReportType = 'research' | 'analysis' | 'performance' | 'risk'

// 报告格式
export type ReportFormat = 'pdf' | 'json' | 'html' | 'csv'

// 报告响应数据
export interface ReportResponse {
  id: string
  task_id: string
  user_id: string
  type: ReportType
  title: string
  summary: string
  content: Record<string, any>
  metadata: {
    symbol?: string
    timeframe?: string
    generated_at: string
    version: string
    [key: string]: any
  }
  created_at: string
  updated_at: string
}

// 用户统计信息
export interface UserStatistics {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  pending_tasks: number
  total_reports: number
  total_api_calls: number
  total_tokens_used: number
  subscription_tier: string
  usage_this_month: {
    tasks: number
    reports: number
    api_calls: number
    tokens: number
  }
  limits: {
    tasks_per_month: number
    reports_per_month: number
    api_calls_per_month: number
    tokens_per_month: number
  }
}

// 分页参数
export interface PaginationParams {
  page?: number
  size?: number
  sort?: string
  order?: 'asc' | 'desc'
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}