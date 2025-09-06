// 研究报告相关类型定义

export interface ResearchReport {
  id: string
  title: string
  symbol: string
  description: string
  content: string
  summary: string
  
  // 元数据
  createdAt: string
  updatedAt: string
  version: number
  author: string
  
  // 分析配置
  analysisConfig: {
    timeframe: string
    depth: number
    analysts: string[]
    llmProvider: string
    llmModel: string
  }
  
  // 分析结果
  analysisResults: {
    score: number
    recommendation: 'buy' | 'sell' | 'hold'
    confidence: number
    keyFindings: string[]
    risks: string[]
    opportunities: string[]
  }
  
  // 分类和标签
  category: ReportCategory
  tags: ReportTag[]
  
  // 状态信息
  status: 'draft' | 'completed' | 'archived' | 'shared'
  isFavorite: boolean
  isPublic: boolean
  
  // 统计信息
  stats: {
    views: number
    shares: number
    downloads: number
    likes: number
  }
  
  // 成本信息
  costInfo: {
    totalCost: number
    tokenUsage: number
    analysisTime: number
  }
}

export interface ReportCategory {
  id: string
  name: string
  description: string
  color: string
  icon: string
  parentId?: string
  children?: ReportCategory[]
}

export interface ReportTag {
  id: string
  name: string
  color: string
  description?: string
  usageCount: number
  createdAt: string
}

export interface ComparisonSet {
  id: string
  name: string
  description: string
  reports: string[] // 报告ID数组
  createdAt: string
  updatedAt: string
  
  // 对比配置
  config: {
    metrics: ComparisonMetric[]
    timeRange: string
    includeCharts: boolean
    includeDetails: boolean
  }
  
  // 对比结果
  results?: ComparisonResult
}

export interface ComparisonMetric {
  id: string
  name: string
  type: 'score' | 'recommendation' | 'confidence' | 'cost' | 'time'
  weight: number
  enabled: boolean
}

export interface ComparisonResult {
  summary: string
  winner: string // 报告ID
  metrics: {
    [metricId: string]: {
      [reportId: string]: number | string
    }
  }
  charts: ComparisonChart[]
  insights: string[]
}

export interface ComparisonChart {
  type: 'bar' | 'line' | 'radar' | 'pie'
  title: string
  data: any
  config: any
}

export interface ShareConfig {
  id: string
  reportId: string
  shareType: 'link' | 'email' | 'export'
  permissions: SharePermission[]
  expiresAt?: string
  password?: string
  downloadEnabled: boolean
  commentsEnabled: boolean
  createdAt: string
}

export interface SharePermission {
  userId?: string
  email?: string
  role: 'viewer' | 'commenter' | 'editor'
  grantedAt: string
}

export interface ReportComment {
  id: string
  reportId: string
  userId: string
  userName: string
  userAvatar?: string
  content: string
  parentId?: string
  replies?: ReportComment[]
  createdAt: string
  updatedAt: string
  isEdited: boolean
  likes: number
}

export interface ExportConfig {
  format: 'pdf' | 'excel' | 'markdown' | 'json'
  includeCharts: boolean
  includeRawData: boolean
  includeMetadata: boolean
  customTemplate?: string
  watermark?: string
}

export interface SearchFilter {
  query?: string
  categories?: string[]
  tags?: string[]
  dateRange?: {
    start: string
    end: string
  }
  status?: string[]
  symbols?: string[]
  sortBy?: 'createdAt' | 'updatedAt' | 'score' | 'title' | 'views'
  sortOrder?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export interface SearchResult {
  reports: ResearchReport[]
  total: number
  hasMore: boolean
  facets: {
    categories: { [key: string]: number }
    tags: { [key: string]: number }
    symbols: { [key: string]: number }
    status: { [key: string]: number }
  }
}

export interface BatchOperation {
  type: 'delete' | 'archive' | 'tag' | 'category' | 'export'
  reportIds: string[]
  params?: any
}

export interface ReportTemplate {
  id: string
  name: string
  description: string
  structure: {
    sections: TemplateSection[]
  }
  isDefault: boolean
  createdAt: string
}

export interface TemplateSection {
  id: string
  title: string
  type: 'text' | 'chart' | 'table' | 'metrics'
  required: boolean
  order: number
  config?: any
}

export interface ReportAnalytics {
  reportId: string
  period: string
  metrics: {
    views: DailyMetric[]
    shares: DailyMetric[]
    downloads: DailyMetric[]
    likes: DailyMetric[]
  }
  topReferrers: string[]
  userEngagement: {
    averageReadTime: number
    bounceRate: number
    returnVisitors: number
  }
}

export interface DailyMetric {
  date: string
  value: number
}

export interface ResearchWorkspace {
  id: string
  name: string
  description: string
  ownerId: string
  members: WorkspaceMember[]
  reports: string[]
  categories: ReportCategory[]
  tags: ReportTag[]
  settings: WorkspaceSettings
  createdAt: string
  updatedAt: string
}

export interface WorkspaceMember {
  userId: string
  userName: string
  email: string
  role: 'owner' | 'admin' | 'editor' | 'viewer'
  joinedAt: string
  lastActiveAt: string
}

export interface WorkspaceSettings {
  isPublic: boolean
  allowGuestComments: boolean
  requireApproval: boolean
  defaultSharePermission: 'viewer' | 'commenter' | 'editor'
  retentionPolicy: {
    archiveAfterDays: number
    deleteAfterDays: number
  }
} 