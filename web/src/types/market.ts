/**
 * 市场类型定义
 */

// 市场类型
export type MarketType = 'crypto'

// 符号预设
export interface SymbolPreset {
  value: string
  label: string
  category: MarketType
}

// 时间范围
export interface TimeFrame {
  value: string
  label: string // i18n key
}

// 市场配置
export interface MarketConfig {
  id: MarketType
  name: string // i18n key
  icon: string
  hasTimeFrame: boolean
  hasDepthConfig: boolean
  defaultDepth: number
  depthRange: { min: number; max: number }
  symbolPresets: SymbolPreset[]
  defaultTimeFrame?: string
  availableTimeFrames?: TimeFrame[]
  // 动态智能体配置
  features?: {
    dynamicAgents?: boolean
  }
  agentAnimationDuration?: number
  maxVisibleAgents?: number
  agentChipSize?: { width: number; height: number }
  debateLineColor?: string
  riskDiscussionLineColor?: string
}