/**
 * 市场配置端口接口
 */
import type { MarketType, MarketConfig } from '@/types/market'

/**
 * 市场配置端口接口
 */
export interface IMarketConfigPort {
  /**
   * 获取可用的市场类型列表
   */
  getAvailableMarkets(): Promise<MarketType[]>
  
  /**
   * 获取指定市场的配置
   */
  getMarketConfig(marketType: MarketType): Promise<MarketConfig | null>
  
  /**
   * 获取默认市场类型
   */
  getDefaultMarket(): Promise<MarketType>
}