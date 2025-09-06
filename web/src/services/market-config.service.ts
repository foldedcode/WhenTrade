/**
 * 市场配置服务
 * 提供市场配置的业务逻辑层
 */
import type { IMarketConfigPort } from '@/ports/market-config.port'
import type { MarketType, MarketConfig } from '@/types/market'
import { marketConfigAdapter } from '@/adapters/market-config.adapter'

export class MarketConfigService {
  private adapter: IMarketConfigPort
  private cache: Map<string, { data: any; timestamp: number }> = new Map()
  private readonly CACHE_TTL = 5 * 60 * 1000 // 5分钟缓存

  constructor(adapter: IMarketConfigPort = marketConfigAdapter) {
    this.adapter = adapter
  }

  /**
   * 获取可用市场列表（带缓存）
   */
  async getAvailableMarkets(): Promise<MarketType[]> {
    const cacheKey = 'available-markets'
    const cached = this.getFromCache(cacheKey)
    
    if (cached) {
      return cached as MarketType[]
    }
    
    const markets = await this.adapter.getAvailableMarkets()
    this.setCache(cacheKey, markets)
    
    return markets
  }

  /**
   * 获取市场配置（带缓存）
   */
  async getMarketConfig(marketType: MarketType): Promise<MarketConfig | null> {
    const cacheKey = `market-config-${marketType}`
    const cached = this.getFromCache(cacheKey)
    
    if (cached) {
      return cached as MarketConfig
    }
    
    const config = await this.adapter.getMarketConfig(marketType)
    if (config) {
      this.setCache(cacheKey, config)
    }
    
    return config
  }

  /**
   * 获取默认市场
   */
  async getDefaultMarket(): Promise<MarketType> {
    const cacheKey = 'default-market'
    const cached = this.getFromCache(cacheKey)
    
    if (cached) {
      return cached as MarketType
    }
    
    const defaultMarket = await this.adapter.getDefaultMarket()
    this.setCache(cacheKey, defaultMarket)
    
    return defaultMarket
  }

  /**
   * 批量获取市场配置
   */
  async getMarketConfigs(marketTypes: MarketType[]): Promise<Map<MarketType, MarketConfig>> {
    const configs = new Map<MarketType, MarketConfig>()
    
    // 并行获取所有配置
    const promises = marketTypes.map(async (marketType) => {
      const config = await this.getMarketConfig(marketType)
      if (config) {
        configs.set(marketType, config)
      }
    })
    
    await Promise.all(promises)
    return configs
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear()
  }

  /**
   * 清除指定缓存
   */
  clearCacheFor(marketType?: MarketType): void {
    if (marketType) {
      this.cache.delete(`market-config-${marketType}`)
    } else {
      this.cache.delete('available-markets')
      this.cache.delete('default-market')
    }
  }

  private getFromCache(key: string): any | null {
    const cached = this.cache.get(key)
    if (!cached) return null
    
    const isExpired = Date.now() - cached.timestamp > this.CACHE_TTL
    if (isExpired) {
      this.cache.delete(key)
      return null
    }
    
    return cached.data
  }

  private setCache(key: string, data: any): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }
}

// 导出单例
export const marketConfigService = new MarketConfigService()