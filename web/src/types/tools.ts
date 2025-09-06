/**
 * 工具相关类型定义
 */

export interface Tool {
  name: string
  description: string
  type: string
  version: string
  parameters: Record<string, ToolParameter>
  features?: Record<string, any>
  dependencies?: string[]
  tags?: string[]
  usage?: number
}

export interface ToolParameter {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object'
  default?: any
  min?: number
  max?: number
  enum?: string[]
  description?: string
  required?: boolean
}

export interface ToolExecutionRequest {
  tool_name: string
  symbol: string
  market_type?: string
  timeframe?: string
  parameters?: Record<string, any>
}

export interface ToolResult {
  tool_name: string
  success: boolean
  data?: any
  error?: string
  metadata?: Record<string, any>
  timestamp: string
}

export interface WorkflowRequest {
  workflow: string[][]
  symbol: string
  market_type?: string
  timeframe?: string
  parameters?: Record<string, any>
}

export interface WorkflowResult {
  workflow: string[][]
  stages: Array<{
    stage: number
    tools: string[]
    results: Record<string, ToolResult>
  }>
  completed: boolean
}

export interface ToolExecutionHistory {
  tool_name: string
  execution_id: string
  context: {
    symbol: string
    market_type: string
    timeframe: string
    user_id: string
  }
  result: ToolResult
  executed_at: string
}

export type ToolType = 'technical' | 'sentiment' | 'fundamental' | 'macro' | 'custom'

// 用户工具相关类型
export interface UserToolResponse {
  tool_id: string
  tool_name: string
  tool_type: 'builtin' | 'mcp'
  category: string
  description: string
  is_connected: boolean
  configuration?: Record<string, any>
  permissions?: string[]
  connected_at?: string
  last_used?: string
  usage_count: number
}

export interface ToolConfigurationRequest {
  configuration: Record<string, any>
}

export interface ToolConnectRequest {
  tool_type: 'builtin' | 'mcp'
  configuration?: Record<string, any>
}

export interface ToolPermissionsUpdateRequest {
  permissions: string[]
}

export interface MCPConnectionResponse {
  connection_id: string
  server_name: string
  transport_type: string
  status: 'connected' | 'disconnected' | 'error'
  connected_at?: string
  error_message?: string
  available_tools: string[]
}

export interface MCPConnectRequest {
  server_name: string
  transport_type: 'stdio' | 'websocket'
  transport_config: Record<string, any>
}

export interface ToolStatsResponse {
  total_tools: number
  connected_tools: number
  mcp_connections: number
  usage_today: number
  usage_this_month: number
  most_used_tools: Array<{
    tool_name: string
    usage_count: number
  }>
}

export interface MarketplaceToolResponse {
  tool_id: string
  name: string
  description: string
  category: string
  author: string
  version: string
  rating: number
  install_count: number
  tags: string[]
  pricing: {
    type: 'free' | 'paid' | 'subscription'
    price?: number
    currency?: string
  }
}

export interface ToolListResponse {
  tools: UserToolResponse[]
  total: number
}

export interface MCPConnectionListResponse {
  connections: MCPConnectionResponse[]
  total: number
}

export interface MarketplaceRecommendationsResponse {
  recommendations: MarketplaceToolResponse[]
}

export type ToolTypeEnum = ToolType