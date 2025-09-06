// API 基础类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// 分析相关类型
export interface AnalysisRequest {
  symbol: string
  timeframe?: string
  depth?: number
  analysts?: string[]
  llm_provider?: string
  llm_model?: string
}

export interface AnalysisResponse {
  symbol: string
  timeframe: string
  analysis_depth: number
  timing_score: number
  recommendation: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  entry_points: Array<{
    price: number
    probability: number
  }>
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
  timestamp: string
  analysis_summary: string
  detailed_analysis: Record<string, any>
}

export interface SentimentResponse {
  symbol: string
  sentiment_score: number
  sentiment_label: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  news_impact: number
  social_sentiment: number
  technical_sentiment: number
  timestamp: string
}

export interface BatchAnalysisRequest {
  symbols: string[]
  analysis_types: string[]
  config?: Record<string, any>
}

export interface BatchAnalysisResponse {
  results: AnalysisResponse[]
  total_cost: number
  execution_time: number
  status: 'completed' | 'partial' | 'failed'
}

// 工作流相关类型
export interface WorkflowExecution {
  workflow_id: string
  started_at: string
  completed_at?: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  current_step?: string
  results: Record<string, any>
  error?: string
}

export interface WorkflowNode {
  id: string
  name: string
  node_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  dependencies: string[]
  result?: any
  error?: string
  metadata?: Record<string, any>
  started_at?: string
  completed_at?: string
}

// 成本管理类型
export interface CostItem {
  service: string
  operation: string
  amount: number
  currency: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface CostLimits {
  daily_limit: number
  weekly_limit: number
  monthly_limit: number
  per_analysis_limit: number
  currency: string
}

export interface CostSummary {
  total_spent: number
  daily_spent: number
  weekly_spent: number
  monthly_spent: number
  remaining_budget: number
  currency: string
  last_updated: string
}

// 移除了市场数据类型定义，因为与AI研究平台核心功能不符

export interface KlineResponse {
  // 移除了KlineResponse内容
}

// 投资组合类型
export interface Position {
  symbol: string
  quantity: number
  average_price: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
}

export interface PortfolioResponse {
  user_id: string
  total_value: number
  total_pnl: number
  total_pnl_percent: number
  positions: Position[]
  cash_balance: number
  last_updated: string
}

// WebSocket 消息类型
export interface WebSocketMessage {
  type: 'workflow_update' | 'cost_update' | 'market_update' | 'error'
  data: any
  timestamp: string
}

export interface WorkflowUpdateMessage extends WebSocketMessage {
  type: 'workflow_update'
  data: WorkflowExecution
}

export interface CostUpdateMessage extends WebSocketMessage {
  type: 'cost_update'
  data: CostItem
}

// 移除了MarketUpdateMessage，因为与AI研究平台核心功能不符 