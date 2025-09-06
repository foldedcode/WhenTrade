/**
 * 配置服务 - 从后端动态获取配置
 * 消除前端硬编码，实现配置集中管理
 */

import request from '@/utils/request'

// 配置缓存
const configCache = new Map<string, any>()
const CACHE_TTL = 5 * 60 * 1000 // 5分钟缓存

interface CacheEntry {
  data: any
  timestamp: number
}

/**
 * 获取系统配置
 */
export async function getSystemConfig() {
  const cacheKey = 'system_config'
  const cached = configCache.get(cacheKey) as CacheEntry
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  
  try {
    const data = await request.get('/api/v1/config/system')
    
    configCache.set(cacheKey, {
      data,
      timestamp: Date.now()
    })
    
    return data
  } catch (error) {
    console.error('Failed to fetch system config:', error)
    // 返回默认配置作为降级方案
    return getDefaultSystemConfig()
  }
}

/**
 * 获取市场配置
 */
export async function getMarketConfig(marketType: string) {
  const cacheKey = `market_${marketType}`
  const cached = configCache.get(cacheKey) as CacheEntry
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  
  try {
    const data = await request.get(`/api/v1/config/markets/${marketType}`)
    
    configCache.set(cacheKey, {
      data,
      timestamp: Date.now()
    })
    
    return data
  } catch (error) {
    console.error(`Failed to fetch market config for ${marketType}:`, error)
    return getDefaultMarketConfig(marketType)
  }
}

/**
 * 获取分析范围配置
 */
export async function getAnalysisScopes(marketType: string) {
  const cacheKey = `scopes_${marketType}`
  const cached = configCache.get(cacheKey) as CacheEntry
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  
  try {
    const data = await request.get(`/api/v1/config/analysis-scopes/${marketType}`)
    
    configCache.set(cacheKey, {
      data,
      timestamp: Date.now()
    })
    
    return data
  } catch (error) {
    console.error(`Failed to fetch analysis scopes for ${marketType}:`, error)
    return []
  }
}

/**
 * 清除配置缓存
 */
export function clearConfigCache() {
  configCache.clear()
}

/**
 * 默认系统配置（降级方案）
 */
function getDefaultSystemConfig() {
  return {
    markets: [
      { market_type: 'crypto', name: '加密货币' },
      { market_type: 'us', name: '美股' },
      { market_type: 'china', name: 'A股' }
    ],
    analysis_depths: {
      1: { name: '快速', description: '基础分析，1-2分钟' },
      2: { name: '标准', description: '标准分析，3-5分钟' },
      3: { name: '深度', description: '深度分析，5-10分钟' },
      4: { name: '专业', description: '专业分析，10-15分钟' },
      5: { name: '极致', description: '全面分析，15分钟以上' }
    },
    llm_providers: ['deepseek', 'kimi', 'openai', 'anthropic'],
    defaults: {
      max_tokens: 4096,
      temperature: 0.7,
      timeout: 60
    }
  }
}

/**
 * 默认市场配置（降级方案）
 */
function getDefaultMarketConfig(marketType: string) {
  const configs: Record<string, any> = {
    crypto: {
      market_type: 'crypto',
      name: '加密货币',
      supported_scopes: ['technical', 'onchain', 'defi', 'sentiment', 'news'],
      default_agents: ['market_analyst', 'onchain_analyst', 'defi_analyst']
    }
  }
  
  return configs[marketType] || configs.crypto
}