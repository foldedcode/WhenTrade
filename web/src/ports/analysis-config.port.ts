/**
 * 分析配置端口接口
 */
import type { AnalysisScope } from '@/types/analysis'
import type { MarketType } from '@/types/market'

/**
 * 分析表单数据
 */
export interface AnalysisFormData {
  marketType: MarketType
  symbol: string
  timeframe?: string
  depth: number
  analysisScopes: string[]
  llmProvider: string
  llmModel: string
  scopeConfigs?: Record<string, { tools: string[], dataSources: string[] }>  // Phase 2: 工具配置
}

/**
 * 验证结果
 */
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings?: string[]
}

/**
 * 市场表单配置
 */
export interface MarketFormConfig {
  hasTimeFrame: boolean
  hasDepthConfig: boolean
  availableScopes: AnalysisScope[]
  defaultValues: Partial<AnalysisFormData>
}

/**
 * 分析配置端口接口
 */
export interface IAnalysisConfigPort {
  /**
   * 获取市场支持的分析范围
   */
  getAnalysisScopes(marketType: MarketType): Promise<AnalysisScope[]>
  
  /**
   * 验证分析配置
   */
  validateAnalysisConfig(config: AnalysisFormData): Promise<ValidationResult>
  
  /**
   * 转换为API参数
   */
  transformToApiParams(config: AnalysisFormData): Promise<Record<string, any>>
  
  /**
   * 获取市场的表单配置
   */
  getFormConfigForMarket(marketType: MarketType): Promise<MarketFormConfig | null>
}