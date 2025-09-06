/**
 * 市场配置适配器实现
 */
import type { IMarketConfigPort } from '@/ports/market-config.port'
import type { MarketType, MarketConfig } from '@/types/market'
import { AVAILABLE_MARKETS, MARKET_CONFIGS, DEFAULT_MARKET } from '@/config/markets'

/**
 * 市场配置适配器
 * 从配置文件和环境变量读取市场配置
 */
export class MarketConfigAdapter implements IMarketConfigPort {
  /**
   * 获取可用的市场类型列表
   */
  async getAvailableMarkets(): Promise<MarketType[]> {
    // 可以从环境变量覆盖
    const envMarkets = import.meta.env.VITE_AVAILABLE_MARKETS
    if (envMarkets) {
      const markets = envMarkets.split(',').map((m: string) => m.trim()) as MarketType[]
      return markets.filter(m => AVAILABLE_MARKETS.includes(m))
    }
    
    return AVAILABLE_MARKETS
  }
  
  /**
   * 获取指定市场的配置
   */
  async getMarketConfig(marketType: MarketType): Promise<MarketConfig | null> {
    const config = MARKET_CONFIGS[marketType]
    if (!config) {
      console.warn(`Market config not found for: ${marketType}`)
      return null
    }
    
    return { ...config }
  }
  
  /**
   * 获取默认市场类型
   */
  async getDefaultMarket(): Promise<MarketType> {
    // 优先使用环境变量
    const envDefault = import.meta.env.VITE_DEFAULT_MARKET as MarketType
    if (envDefault && AVAILABLE_MARKETS.includes(envDefault)) {
      return envDefault
    }
    
    return DEFAULT_MARKET
  }
}

// 导出单例
export const marketConfigAdapter = new MarketConfigAdapter()