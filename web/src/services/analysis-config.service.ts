/**
 * 分析配置服务
 * 处理分析配置的业务逻辑
 */
import type { IAnalysisConfigPort, AnalysisFormData, ValidationResult, MarketFormConfig } from '@/ports/analysis-config.port'
import type { AnalysisScope } from '@/types/analysis'
import type { MarketType } from '@/types/market'
import { analysisConfigAdapter } from '@/adapters/analysis-config.adapter'

export class AnalysisConfigService {
  private adapter: IAnalysisConfigPort
  private scopeCache: Map<MarketType, AnalysisScope[]> = new Map()
  private formConfigCache: Map<MarketType, MarketFormConfig> = new Map()

  constructor(adapter: IAnalysisConfigPort = analysisConfigAdapter) {
    this.adapter = adapter
  }

  /**
   * 获取市场的分析范围（带缓存）
   */
  async getAnalysisScopes(marketType: MarketType): Promise<AnalysisScope[]> {
    // 检查缓存
    const cached = this.scopeCache.get(marketType)
    if (cached) {
      return cached
    }

    // 从适配器获取
    const scopes = await this.adapter.getAnalysisScopes(marketType)
    
    // 缓存结果
    this.scopeCache.set(marketType, scopes)
    
    return scopes
  }

  /**
   * 验证分析配置
   */
  async validateAnalysisConfig(config: AnalysisFormData): Promise<ValidationResult> {
    return this.adapter.validateAnalysisConfig(config)
  }

  /**
   * 转换为API参数
   */
  async transformToApiParams(config: AnalysisFormData): Promise<Record<string, any>> {
    // 先验证配置
    const validation = await this.validateAnalysisConfig(config)
    if (!validation.valid) {
      const errorMessage = validation.errors.join('; ')
      const error = new Error(`Invalid configuration: ${errorMessage}`)
      ;(error as any).validation = validation
      throw error
    }

    return this.adapter.transformToApiParams(config)
  }

  /**
   * 获取市场的表单配置（带缓存）
   */
  async getFormConfigForMarket(marketType: MarketType): Promise<MarketFormConfig | null> {
    // 检查缓存
    const cached = this.formConfigCache.get(marketType)
    if (cached) {
      return cached
    }

    // 从适配器获取
    const formConfig = await this.adapter.getFormConfigForMarket(marketType)
    
    if (formConfig) {
      // 缓存结果
      this.formConfigCache.set(marketType, formConfig)
    }
    
    return formConfig
  }

  /**
   * 创建默认配置
   */
  async createDefaultConfig(marketType: MarketType): Promise<AnalysisFormData | null> {
    const formConfig = await this.getFormConfigForMarket(marketType)
    if (!formConfig || !formConfig.defaultValues) {
      return null
    }

    return {
      marketType,
      symbol: '',
      timeframe: formConfig.defaultValues.timeframe,
      depth: formConfig.defaultValues.depth || 3,
      analysisScopes: formConfig.defaultValues.analysisScopes || [],
      llmProvider: 'openai',
      llmModel: 'gpt-4-turbo-preview'
    }
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.scopeCache.clear()
    this.formConfigCache.clear()
  }

  /**
   * 清除指定市场的缓存
   */
  clearCacheFor(marketType: MarketType): void {
    this.scopeCache.delete(marketType)
    this.formConfigCache.delete(marketType)
  }

  /**
   * 批量验证配置
   */
  async batchValidate(configs: AnalysisFormData[]): Promise<Map<number, ValidationResult>> {
    const results = new Map<number, ValidationResult>()
    
    const promises = configs.map(async (config, index) => {
      const result = await this.validateAnalysisConfig(config)
      results.set(index, result)
    })
    
    await Promise.all(promises)
    return results
  }
}

// 导出单例
export const analysisConfigService = new AnalysisConfigService()