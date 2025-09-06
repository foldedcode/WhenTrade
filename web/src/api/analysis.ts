/**
 * 分析相关API接口
 */
import { apiClient } from './client'

export interface StartAnalysisRequest {
  market_type: string
  symbol: string
  timeframe: string
  depth: string
  analysis_scopes: string[]
  llm_provider?: string
  llm_model?: string
}

export interface AnalysisStepResponse {
  id: string
  name: string
  description: string
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface AgentResponse {
  id: string
  name: string
  type: string
  status: string
  progress: number
  thoughts: string[]
  confidence: number
  current_task: string
}

export interface AnalysisResultResponse {
  id: string
  symbol: string
  recommendation: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  current_price: number
  target_price: number
  stop_loss: number
  analysis: {
    technical: any
    fundamental: any
    sentiment: any
    risk: any
    signal?: any
  }
  agents_insights: Record<string, any>
  timestamp: number
}

export interface AnalysisHistoryResponse {
  id: string
  config: StartAnalysisRequest
  result: AnalysisResultResponse
  timestamp: number
  duration: number
  cost: number
  steps: AnalysisStepResponse[]
}

// 开始分析
export async function startAnalysis(request: StartAnalysisRequest): Promise<{ analysis_id: string }> {
  // 将请求转换为后端期待的格式
  const response = await apiClient.post('/api/v1/analysis/tasks', {
    symbol: request.symbol,
    analysis_type: 'comprehensive',
    timeframe: request.timeframe || '1d',
    parameters: {
      market_type: request.market_type,
      depth: Number(request.depth) || 3,  // 确保depth是数字类型
      analysis_scopes: Array.isArray(request.analysis_scopes) ? request.analysis_scopes : [],
      analysts: Array.isArray(request.analysis_scopes) ? request.analysis_scopes : [],
      llm_provider: request.llm_provider,
      llm_model: request.llm_model
    }
  })
  
  // 返回分析任务ID
  return { analysis_id: response.id }
}

// 获取分析状态
export async function getAnalysisStatus(analysisId: string): Promise<{
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  current_step?: AnalysisStepResponse
  agents?: AgentResponse[]
  error?: string
}> {
  const response = await apiClient.get(`/api/v1/analysis/tasks/${analysisId}`)
  
  // 适配后端响应格式到前端期望格式
  const taskData = response.data
  return {
    status: taskData.status === 'pending' ? 'pending' : 
            taskData.status === 'processing' ? 'running' :
            taskData.status === 'completed' ? 'completed' : 'failed',
    progress: taskData.status === 'completed' ? 100 : 
              taskData.status === 'processing' ? 50 : 0,
    current_step: taskData.status === 'processing' ? {
      id: 'current',
      name: 'Processing Analysis',
      description: `Analyzing ${taskData.symbol}`,
      progress: 50,
      status: 'running'
    } : undefined,
    agents: [], // 暂时返回空数组，后续可通过WebSocket获取
    error: taskData.status === 'failed' ? 'Analysis failed' : undefined
  }
}

// 获取分析结果
export async function getAnalysisResult(analysisId: string): Promise<AnalysisResultResponse> {
  const response = await apiClient.get(`/api/v1/analysis/tasks/${analysisId}`)
  const taskData = response.data
  
  // 如果任务还未完成，返回默认结果
  if (taskData.status !== 'completed') {
    throw new Error('Analysis not completed yet')
  }
  
  // 从真实的分析结果中提取数据
  const analysisResult = taskData.result || {}
  
  // 提取投资建议和置信度
  let recommendation: 'BUY' | 'SELL' | 'HOLD' = 'HOLD'
  let confidence = 0
  
  // 从多个可能的字段中提取推荐，优先使用signal字段
  if (analysisResult.signal && analysisResult.signal.action) {
    const action = analysisResult.signal.action
    // 过滤硬编码的默认值
    if (action !== "持有" && action !== "无有效信号" && action.trim() !== "") {
      if (action.includes('买') || action.toLowerCase().includes('buy')) {
        recommendation = 'BUY'
      } else if (action.includes('卖') || action.toLowerCase().includes('sell')) {
        recommendation = 'SELL'
      } else if (action.includes('持有') || action.toLowerCase().includes('hold')) {
        recommendation = 'HOLD'
      }
    }
  } else if (analysisResult.portfolio_decision) {
    // 从portfolio_decision文本中解析建议
    const decision = analysisResult.portfolio_decision.toLowerCase()
    if (decision.includes('买入') || decision.includes('buy')) {
      recommendation = 'BUY'
    } else if (decision.includes('卖出') || decision.includes('sell')) {
      recommendation = 'SELL'
    } else if (decision.includes('持有') || decision.includes('hold')) {
      recommendation = 'HOLD'
    }
  } else if (analysisResult.final_recommendation) {
    const finalRec = analysisResult.final_recommendation.toLowerCase()
    if (finalRec.includes('买入') || finalRec.includes('buy')) {
      recommendation = 'BUY'
    } else if (finalRec.includes('卖出') || finalRec.includes('sell')) {
      recommendation = 'SELL'
    } else if (finalRec.includes('持有') || finalRec.includes('hold')) {
      recommendation = 'HOLD'
    }
  }
  
  // 从分析结果中提取置信度，优先使用signal字段
  if (analysisResult.signal?.confidence && 
      analysisResult.signal.confidence !== 0.5 && 
      analysisResult.signal.confidence > 0) {
    confidence = analysisResult.signal.confidence
  } else if (analysisResult.confidence) {
    confidence = typeof analysisResult.confidence === 'number' ? analysisResult.confidence : 0
  } else if (analysisResult.summary?.confidence) {
    confidence = analysisResult.summary.confidence
  }
  
  // 提取价格信息，优先使用signal字段的真实数据
  let currentPrice = analysisResult.current_price || analysisResult.currentPrice || 0
  let targetPrice = 0
  let stopLoss = 0
  
  // 从signal提取目标价格（过滤默认值0）
  if (analysisResult.signal?.target_price && analysisResult.signal.target_price > 0) {
    targetPrice = analysisResult.signal.target_price
  } else {
    targetPrice = analysisResult.target_price || analysisResult.targetPrice || 0
  }
  
  // 提取止损价格
  stopLoss = analysisResult.stop_loss || analysisResult.stopLoss || 0
  
  return {
    id: taskData.id,
    symbol: taskData.symbol,
    recommendation,
    confidence,
    current_price: currentPrice,
    target_price: targetPrice,
    stop_loss: stopLoss,
    analysis: {
      technical: analysisResult.market_report ? { summary: analysisResult.market_report } : {},
      fundamental: analysisResult.fundamentals_report ? { summary: analysisResult.fundamentals_report } : {},
      sentiment: analysisResult.social_report || analysisResult.news_report ? { 
        summary: [analysisResult.social_report, analysisResult.news_report].filter(Boolean).join('\n\n') 
      } : {},
      risk: analysisResult.trade_decision ? { summary: analysisResult.trade_decision } : {},
      // 添加 signal 推理信息
      signal: analysisResult.signal?.reasoning && 
              analysisResult.signal.reasoning !== "无有效信号" && 
              analysisResult.signal.reasoning.trim() !== "" ? {
        summary: analysisResult.signal.reasoning,
        riskScore: analysisResult.signal.risk_score !== 0.5 ? analysisResult.signal.risk_score : undefined
      } : {}
    },
    agents_insights: analysisResult,
    timestamp: new Date(taskData.created_at).getTime()
  }
}

// 停止分析
export async function stopAnalysis(analysisId: string): Promise<void> {
  await apiClient.delete(`/api/v1/analysis/tasks/${analysisId}`)
}

// 获取分析历史
export async function getAnalysisHistory(params?: {
  limit?: number
  offset?: number
  symbol?: string
}): Promise<{
  items: AnalysisHistoryResponse[]
  total: number
}> {
  const response = await apiClient.get('/api/v1/analysis/history', { params })
  return response.data
}

// 获取智能体列表
export async function getAgents(): Promise<AgentResponse[]> {
  const response = await apiClient.get('/api/v1/agents')
  return response.data
}

// 获取智能体状态
export async function getAgentStatus(agentId: string): Promise<AgentResponse> {
  const response = await apiClient.get(`/api/v1/agents/${agentId}/status`)
  return response.data
}

// 获取智能体团队配置
export interface AgentTeamConfig {
  displayName: string
  name: string
  agents: Array<{
    id: string
    name: string
    type: string
    status: string
  }>
}

export interface AgentTeamsResponse {
  marketType: string
  teams: Record<string, AgentTeamConfig>
}

export async function getAgentTeams(
  marketType: string = 'crypto', 
  analysisScopes?: string[]
): Promise<AgentTeamsResponse> {
  const params: any = { market_type: marketType }
  
  // 如果提供了分析范围，添加到参数中
  if (analysisScopes && analysisScopes.length > 0) {
    params.analysis_scopes = analysisScopes.join(',')
  }
  
  const response = await apiClient.get('/api/v1/agents/teams', { params })
  return response.data.data
}

// 取消分析任务（别名）
export const cancelAnalysisTask = stopAnalysis

// 导出API对象
export const analysisApi = {
  startAnalysis,
  getAnalysisStatus,
  getAnalysisResult,
  stopAnalysis,
  cancelAnalysisTask,  // 添加取消任务别名
  getAnalysisHistory,
  getAgents,
  getAgentStatus,
  getAgentTeams,
  apiClient  // 导出apiClient以便直接使用
}