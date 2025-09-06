/**
 * 市场配置
 */
import type { MarketType, MarketConfig } from '@/types/market'

// 可用市场类型
export const AVAILABLE_MARKETS: MarketType[] = ['crypto']

// 默认市场
export const DEFAULT_MARKET: MarketType = 'crypto'

// 市场配置详情
export const MARKET_CONFIGS: Record<MarketType, MarketConfig> = {
  crypto: {
    id: 'crypto',
    name: 'common.marketTypes.crypto',
    icon: '₿',
    hasTimeFrame: true,
    hasDepthConfig: true,
    defaultDepth: 3,
    depthRange: { min: 1, max: 5 },
    defaultTimeFrame: '1h',
    availableTimeFrames: [
      { value: '15m', label: 'analysis.timeFrames.15m' },
      { value: '1h', label: 'analysis.timeFrames.1h' },
      { value: '4h', label: 'analysis.timeFrames.4h' },
      { value: '1d', label: 'analysis.timeFrames.1d' },
      { value: '1w', label: 'analysis.timeFrames.1w' }
    ],
    symbolPresets: [
      { value: 'BTC/USDT', label: 'Bitcoin', category: 'crypto' },
      { value: 'ETH/USDT', label: 'Ethereum', category: 'crypto' },
      { value: 'BNB/USDT', label: 'Binance Coin', category: 'crypto' },
      { value: 'SOL/USDT', label: 'Solana', category: 'crypto' },
      { value: 'ADA/USDT', label: 'Cardano', category: 'crypto' },
      { value: 'XRP/USDT', label: 'Ripple', category: 'crypto' },
      { value: 'DOT/USDT', label: 'Polkadot', category: 'crypto' },
      { value: 'DOGE/USDT', label: 'Dogecoin', category: 'crypto' }
    ],
    // 动态智能体配置
    features: {
      dynamicAgents: true
    },
    agentAnimationDuration: 300,
    maxVisibleAgents: 12,
    agentChipSize: { width: 140, height: 60 },
    debateLineColor: '#00ff88',
    riskDiscussionLineColor: '#ff6600'
  }
}

/**
 * 获取市场配置
 */
export function getMarketConfig(marketType: MarketType): MarketConfig | null {
  const config = MARKET_CONFIGS[marketType]
  return config || null
}

/**
 * 获取默认市场配置
 */
export function getDefaultMarketConfig(): MarketConfig {
  return MARKET_CONFIGS[DEFAULT_MARKET]
}