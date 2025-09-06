import { request } from '@/utils/request'

// 响应类型定义
export interface TokenUsageDetail {
  date: string
  model: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost: number
}

export interface TokenUsageSummary {
  total_tokens: number
  total_cost: number
  daily_average: number
  model_breakdown: Record<string, {
    tokens: number
    cost: number
    percentage: number
  }>
}

export interface CostOptimizationSuggestion {
  id: string
  title: string
  description: string
  potential_savings: number
  difficulty: 'easy' | 'medium' | 'hard'
  is_implemented: boolean
}

export interface BudgetSettings {
  daily_limit?: number
  monthly_limit?: number
  alert_threshold: number
}

export interface UserAchievement {
  id: string
  name: string
  description: string
  icon: string
  unlocked_at?: string
  progress: number
}

export interface LeaderboardEntry {
  rank: number
  user_id: string
  username: string
  efficiency_score: number
  total_saved: number
  streak_days: number
}

export interface ModelPricing {
  name: string
  input_price: number
  output_price: number
  description: string
}

export interface ModelSelectionStrategy {
  strategy: 'balanced' | 'cost' | 'quality'
  rules: Record<string, any>
  auto_switch: boolean
}

// API 接口
export const costApi = {
  // 获取使用情况汇总
  getUsageSummary(days: number = 30) {
    return request.get<TokenUsageSummary>('/api/v1/cost/usage/summary', {
      params: { days }
    })
  },

  // 获取详细使用记录
  getUsageDetails(params: {
    start_date?: string
    end_date?: string
    model?: string
    limit?: number
  }) {
    return request.get<TokenUsageDetail[]>('/api/v1/cost/usage/details', {
      params
    })
  },

  // 获取优化建议
  getOptimizationSuggestions() {
    return request.get<CostOptimizationSuggestion[]>('/api/v1/cost/optimization/suggestions')
  },

  // 获取预算设置
  getBudgetSettings() {
    return request.get<BudgetSettings>('/api/v1/cost/budget/settings')
  },

  // 更新预算设置
  updateBudgetSettings(settings: BudgetSettings) {
    return request.put<BudgetSettings>('/api/v1/cost/budget/settings', settings)
  },

  // 获取成就列表
  getAchievements() {
    return request.get<UserAchievement[]>('/api/v1/cost/achievements')
  },

  // 解锁成就
  unlockAchievement(achievementId: string) {
    return request.post(`/api/v1/cost/achievements/${achievementId}/unlock`)
  },

  // 获取排行榜
  getLeaderboard(timeframe: 'daily' | 'weekly' | 'monthly' | 'all_time' = 'monthly', limit: number = 10) {
    return request.get<LeaderboardEntry[]>('/api/v1/cost/leaderboard', {
      params: { timeframe, limit }
    })
  },

  // 获取模型定价
  getModelPricing() {
    return request.get<{ models: ModelPricing[] }>('/api/v1/cost/models/pricing')
  },

  // 获取模型选择策略
  getModelStrategy() {
    return request.get<ModelSelectionStrategy>('/api/v1/cost/model-strategy')
  },

  // 更新模型选择策略
  updateModelStrategy(strategy: ModelSelectionStrategy) {
    return request.put<ModelSelectionStrategy>('/api/v1/cost/model-strategy', strategy)
  },

  // 自动应用优化建议
  autoApplyOptimization(suggestionId: string) {
    return request.post<{ message: string; applied: boolean }>(`/api/v1/cost/optimize/auto-apply/${suggestionId}`)
  }
}