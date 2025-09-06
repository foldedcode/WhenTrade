// 分析范围类型
export interface AnalysisScope {
  id: string
  name: string  // i18n key
  description: string  // i18n key
  icon: string
  marketTypes: string[]  // 支持的市场类型
  defaultTools?: string[]  // 默认工具列表
}

// 分析配置类型
export interface AnalysisConfig {
  marketType?: string  // 市场类型
  symbol: string
  timeframe?: string  // 改为可选，Polymarket不需要
  depth: number
  analysts: string[]  // @deprecated 后续会改为 analysisScopes
  llmProvider: string
  llmModel: string
  tools?: string[]        // Phase 2.5: 用户选择的工具列表
  dataSources?: string[]  // Phase 2.5: 用户选择的数据源列表
}

// 分析步骤类型
export interface AnalysisStep {
  id: string
  name: string
  description: string
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed'
}

// 智能体状态类型
export interface AgentStatus {
  id: string
  name: string
  type: string
  role: string
  status: 'idle' | 'thinking' | 'analyzing' | 'debating' | 'completed' | 'failed'
  progress: number
  currentTask: string
  thoughts: string[]
  confidence: number
  avatar: string
  lastUpdate: string
}

// 价格信息类型
export interface PriceInfo {
  current: number
  target: number
  stopLoss: number
}

// 技术分析类型
export interface TechnicalAnalysis {
  trend: 'bullish' | 'bearish' | 'neutral'
  support: number
  resistance: number
  indicators: {
    rsi: number
    macd: 'bullish' | 'bearish' | 'neutral'
    ma20: number
    ma50: number
  }
}

// 基本面分析类型
export interface FundamentalAnalysis {
  score: number
  factors: string[]
}

// 情绪分析类型
export interface SentimentAnalysis {
  score: number
  social: {
    twitter: number
    reddit: number
    telegram: number
  }
  fearGreed: number
}

// 风险分析类型
export interface RiskAnalysis {
  level: 'low' | 'medium' | 'high'
  factors: string[]
  score: number
}

// 智能体结果类型
export interface AgentResult {
  id: string
  name: string
  confidence: number
  recommendation: 'BUY' | 'SELL' | 'HOLD'
  reasoning: string[]
}

// 分析结果类型 - Linus式简化：消除不必要的嵌套，统一数据结构
export interface AnalysisResult {
  readonly id: string
  readonly symbol: string
  readonly action: 'BUY' | 'SELL' | 'HOLD'  // 重命名为更清晰的action
  readonly confidence: number  // 0-1范围
  readonly price: number       // 简化价格字段
  readonly timestamp: number   // 使用number而不是string
  readonly indicators: ReadonlyMap<string, number>  // 扁平化技术指标
  readonly reasons: readonly string[]  // 简化推理过程
  readonly risk: 'LOW' | 'MEDIUM' | 'HIGH'  // 简化风险评估
  
  // 为向后兼容保留的字段 - 标记为deprecated
  /** @deprecated 使用 action 替代 */
  recommendation?: 'BUY' | 'SELL' | 'HOLD'
  /** @deprecated 使用 price 替代 */
  currentPrice?: number
  /** @deprecated 价格字段已简化 */
  targetPrice?: number
  /** @deprecated 价格字段已简化 */
  stopLoss?: number
  /** @deprecated 使用新的扁平结构 */
  analysis?: {
    technical?: TechnicalAnalysis
    fundamental?: FundamentalAnalysis
    sentiment?: SentimentAnalysis
    risk?: RiskAnalysis
  }
  /** @deprecated 使用number类型的timestamp */
  timestamp_string?: string
  /** @deprecated 使用 reasons 替代 */
  agentAnalysis?: AgentResult[]
}

// 分析历史记录类型
export interface AnalysisHistory {
  id: string
  config: AnalysisConfig
  result: AnalysisResult | null
  report?: string // 完整的Markdown报告内容
  simpleReport?: string // 简洁的Markdown报告内容
  timestamp: number // 改为number类型以匹配Date.now()
  duration: number // 分析耗时（毫秒）
  cost?: number // 分析成本
  steps: AnalysisStep[]
  agentThoughts?: Array<{
    agent: string
    thought: string
    timestamp: string
    phase?: string
    phaseName?: string
    phaseOrder?: number
    isTool?: boolean
    tool?: string
  }> // Agent 思考过程的原始数据
}

// 成本信息类型
export interface CostInfo {
  totalCost: number
  dailyCost: number
  monthlyCost: number
  budget: {
    daily: number
    monthly: number
  }
  usage: {
    tokenCount: number
    apiCalls: number
  }
}

// 工作流状态类型
export interface WorkflowStatus {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  currentStep: string
  steps: AnalysisStep[]
  startTime: string
  endTime?: string
  error?: string
}

// 研究任务类型
export interface Research {
  id: string
  symbol: string
  marketType: 'stock' | 'crypto' | 'commodity'
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  depth: number
  analysts: string[]
  progress: number
  cost: number
  createdAt: string
  completedAt?: string
  reportId?: string
  error?: string
}

// 研究配置类型
export interface ResearchConfig {
  symbol: string
  marketType: 'stock' | 'crypto' | 'commodity'
  depth: number
  analysts: string[]
  llmProvider?: string
  llmModel?: string
  customPrompts?: Record<string, string>
}

// 研究报告类型
export interface ResearchReport {
  id: string
  researchId: string
  symbol: string
  title: string
  summary: string
  content: {
    technicalAnalysis?: any
    fundamentalAnalysis?: any
    sentimentAnalysis?: any
    riskAssessment?: any
  }
  recommendations: string[]
  sentiment?: 'bullish' | 'neutral' | 'bearish'
  confidenceScore?: number
  createdAt: string
}

// 市场类型枚举
export type MarketType = 'stock' | 'crypto' | 'commodity'

// 分析状态枚举
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

// LLM配置类型
export interface LLMConfig {
  provider: string
  model?: string
  temperature?: number
  max_tokens?: number
  system_prompt?: string
}

// 分析请求类型
export interface AnalysisRequest {
  symbol: string
  market_type: MarketType
  analysis_depth?: number
  analysts?: string[]
  llm_config?: LLMConfig
}

// 分析任务类型
export interface AnalysisTask {
  id: string
  user_id: number
  symbol: string
  market_type: MarketType
  analysis_depth: number
  analysts: string[]
  llm_config: Record<string, any>
  status: AnalysisStatus
  progress: number
  error_message?: string
  token_usage: {
    input_tokens: number
    output_tokens: number
  }
  cost_usd: number
  created_at: string
  updated_at: string
  started_at?: string
  completed_at?: string
}

// 分析报告类型
export interface AnalysisReport {
  id: string
  task_id: string
  analyst_type: string
  content: Record<string, any>
  summary: string
  rating?: 'bullish' | 'neutral' | 'bearish'
  confidence_score?: number
  key_findings: any[]
  recommendations: any[]
  created_at: string
}

// 分析日志类型
export interface AnalysisLog {
  id: string
  task_id: string
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'debug'
  agent_name?: string
  message: string
  details?: Record<string, any>
}

// 分析统计类型
export interface AnalysisStatistics {
  task_statistics: Record<AnalysisStatus, number>
  total_reports: number
  total_cost: number
  average_duration_minutes: number
  most_analyzed_symbols: Array<{
    symbol: string
    count: number
  }>
  user_since: string
}

// 动态分析相关类型
// Agent思考类型
export enum ThoughtType {
  OBSERVATION = 'observation',
  ANALYSIS = 'analysis',
  CONCLUSION = 'conclusion',
  QUESTION = 'question'
}

// Agent思考记录
export interface AgentThought {
  id: string
  agentId: string
  domain: string
  timestamp: number
  thoughtType: ThoughtType
  content: string
  confidence?: number
  evidence?: Array<{
    type: string
    value: any
  }>
}

// 动态Agent信息
export interface Agent {
  id: string
  name: string
  domain: string
  status: 'idle' | 'active' | 'completed'
  color?: string
  thoughtCount?: number
  startTime?: number
  currentThought?: {
    type: string
    content: string
  }
}

// 分析阶段
export interface AnalysisStage {
  id: string
  name: string
  status: 'pending' | 'active' | 'completed'
  agentCount: number
  agents?: string[]
}

// 分析领域枚举
export enum AnalysisDomain {
  TECHNICAL = 'technical',
  FUNDAMENTAL = 'fundamental',
  SENTIMENT = 'sentiment',
  RISK = 'risk',
  MARKET = 'market',
  VALUATION = 'valuation',
  SECTOR = 'sector',
  EVENT = 'event',
  PROBABILITY = 'probability',
  ODDS = 'odds',
  LIQUIDITY = 'liquidity',
  INFORMATION = 'information'
} 