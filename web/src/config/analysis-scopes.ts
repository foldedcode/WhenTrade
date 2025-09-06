/**
 * 分析范围配置
 */
import type { AnalysisScope } from '@/types/analysis'
import type { MarketType } from '@/types/market'

// 默认工具配置（每个分析范围的推荐工具）
export const SCOPE_DEFAULT_TOOLS = {
  technical: ['crypto_price', 'indicators', 'market_data', 'historical_data', 'market_metrics', 'trending', 'fear_greed'],
  sentiment: ['finnhub_news', 'reddit_sentiment', 'sentiment_batch'],
} as const

// 所有分析范围定义
export const ANALYSIS_SCOPES: AnalysisScope[] = [
  // 加密货币分析范围
  {
    id: 'technical',
    name: 'analysis.scopes.technical.name',
    description: 'analysis.scopes.technical.description',
    icon: '📊',
    marketTypes: ['crypto'],
    defaultTools: SCOPE_DEFAULT_TOOLS.technical
  },
  {
    id: 'sentiment',
    name: 'analysis.scopes.sentiment.name',
    description: 'analysis.scopes.sentiment.description',
    icon: '💭',
    marketTypes: ['crypto'],
    defaultTools: SCOPE_DEFAULT_TOOLS.sentiment
  }
]

/**
 * 根据市场类型获取可用的分析范围
 */
export function getMarketAnalysisScopes(marketType: MarketType): AnalysisScope[] {
  return ANALYSIS_SCOPES.filter(scope => 
    scope.marketTypes.includes(marketType)
  )
}

/**
 * 根据ID获取分析范围
 */
export function getAnalysisScopeById(id: string): AnalysisScope | undefined {
  return ANALYSIS_SCOPES.find(scope => scope.id === id)
}

/**
 * 验证分析范围是否对市场类型有效
 */
export function isValidScopeForMarket(scopeId: string, marketType: MarketType): boolean {
  const scope = getAnalysisScopeById(scopeId)
  return scope ? scope.marketTypes.includes(marketType) : false
}

/**
 * 获取分析范围的默认工具列表
 */
export function getScopeDefaultTools(scopeId: string): string[] {
  const scope = getAnalysisScopeById(scopeId)
  return scope?.defaultTools || []
}

/**
 * 获取多个分析范围的所有默认工具
 */
export function getMultipleScopesDefaultTools(scopeIds: string[]): Record<string, string[]> {
  const result: Record<string, string[]> = {}
  for (const scopeId of scopeIds) {
    result[scopeId] = getScopeDefaultTools(scopeId)
  }
  return result
}