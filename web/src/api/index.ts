/**
 * API 统一导出 - Linus原则：一个入口，一目了然
 * 
 * 解决 locale.service.ts 的导入问题：
 * import { api } from '@/api' ✅
 */

// 导出核心 API 客户端
export { api, apiClient, ApiError, ErrorCode } from './client'
export type { ApiResponse, RequestConfig } from './client'

// 导出分析相关 API
export * from './analysis'

// 导出性能相关 API
export * from './performance'

// 导出成本相关 API
export { costApi } from './cost'
export type { 
  TokenUsageDetail, 
  TokenUsageSummary, 
  CostOptimizationSuggestion,
  BudgetSettings,
  UserAchievement,
  LeaderboardEntry,
  ModelPricing,
  ModelSelectionStrategy
} from './cost'

// 默认导出主要的 API 对象  
export { api as default }