/**
 * 分析配置适配器实现
 */
import type { IAnalysisConfigPort, AnalysisFormData, ValidationResult, MarketFormConfig } from '@/ports/analysis-config.port'
import type { AnalysisScope } from '@/types/analysis'
import type { MarketType } from '@/types/market'
import { getMarketAnalysisScopes } from '@/config/analysis-scopes'
import { marketConfigAdapter } from './market-config.adapter'
import { getAnalysisScopes } from '@/services/configService'

// 扩展的分析范围类型，包含工具配置
interface ExtendedAnalysisScope extends AnalysisScope {
  availableTools?: Array<{id: string, name: string}>
  availableMCP?: Array<{id: string, name: string}>
  availableDataSources?: Array<{id: string, name: string}>
}

/**
 * 分析配置适配器
 * 处理分析配置的验证和转换
 */
export class AnalysisConfigAdapter implements IAnalysisConfigPort {
  /**
   * 获取市场支持的分析范围
   */
  async getAnalysisScopes(marketType: MarketType): Promise<ExtendedAnalysisScope[]> {
    try {
      // 尝试从后端获取完整的分析范围配置
      const backendScopes = await getAnalysisScopes(marketType)
      if (backendScopes && backendScopes.length > 0) {
        // 确保后端数据使用翻译键格式而不是硬编码文本
        return backendScopes.map((scope: any) => ({
          ...scope,
          // 如果后端返回的是中文硬编码文本，转换为翻译键
          name: scope.name.includes('.') ? scope.name : `analysis.scopes.${scope.id}.name`,
          description: scope.description.includes('.') ? scope.description : `analysis.scopes.${scope.id}.description`
        })) as ExtendedAnalysisScope[]
      }
    } catch (error) {
      console.warn('Failed to fetch scopes from backend, falling back to local config:', error)
    }
    
    // 降级到本地配置
    return getMarketAnalysisScopes(marketType)
  }
  
  /**
   * 验证分析配置
   */
  async validateAnalysisConfig(config: AnalysisFormData): Promise<ValidationResult> {
    const errors: string[] = []
    const warnings: string[] = []
    
    // 验证市场类型
    if (!config.marketType) {
      errors.push('analysis.validation.selectMarket')
    }
    
    // 验证分析标的
    if (!config.symbol || config.symbol.trim().length === 0) {
      errors.push('analysis.validation.enterSymbol')
    }
    
    // 验证分析范围
    if (!config.analysisScopes || config.analysisScopes.length === 0) {
      errors.push('analysis.validation.selectScope')
    } else {
      // 验证选择的范围是否对该市场有效
      const validScopes = await this.getAnalysisScopes(config.marketType)
      const validScopeIds = validScopes.map(s => s.id)
      const invalidScopes = config.analysisScopes.filter(id => !validScopeIds.includes(id))
      
      if (invalidScopes.length > 0) {
        errors.push(`Invalid scopes for ${config.marketType}: ${invalidScopes.join(', ')}`)
      }
    }
    
    // 获取市场配置进行进一步验证
    const marketConfig = await marketConfigAdapter.getMarketConfig(config.marketType)
    if (marketConfig) {
      // 验证时间范围
      if (marketConfig.hasTimeFrame && !config.timeframe) {
        errors.push('Please select a time frame')
      }
      
      // 验证分析深度
      const { min, max } = marketConfig.depthRange
      if (config.depth < min || config.depth > max) {
        errors.push(`Analysis depth must be between ${min} and ${max}`)
      }
    }
    
    // 警告信息
    if (config.analysisScopes.length > 5) {
      warnings.push('Selecting too many analysis scopes may affect performance')
    }
    
    return {
      valid: errors.length === 0,
      errors,
      warnings: warnings.length > 0 ? warnings : undefined
    }
  }
  
  /**
   * 转换为API参数
   */
  async transformToApiParams(config: AnalysisFormData): Promise<Record<string, any>> {
    // Phase 2: 从scopeConfigs中提取工具和数据源
    let selectedTools: string[] = []
    let selectedDataSources: string[] = []
    
    if (config.scopeConfigs) {
      // 合并所有scope的工具和数据源
      Object.values(config.scopeConfigs).forEach(scopeConfig => {
        if (scopeConfig.tools) {
          selectedTools.push(...scopeConfig.tools)
        }
        if (scopeConfig.dataSources) {
          selectedDataSources.push(...scopeConfig.dataSources)
        }
      })
      
      // 去重
      selectedTools = [...new Set(selectedTools)]
      selectedDataSources = [...new Set(selectedDataSources)]
      
      // console.log('📊 [Phase 2] 提取的工具配置:', {
      //   tools: selectedTools,
      //   dataSources: selectedDataSources
      // })
    }
    
    // 【调试】记录接收到的analysisScopes
    // console.log('📊 [AnalysisConfigAdapter] 接收到的analysisScopes:', config.analysisScopes)
    
    // 后端期待的格式：顶层包含 symbol, analysis_type, timeframe
    // 其他参数放在 parameters 对象中
    const params: Record<string, any> = {
      symbol: config.symbol.toUpperCase(),
      analysis_type: 'comprehensive',  // 使用综合分析类型
      timeframe: config.timeframe || '1d',  // 默认使用1天时间框架
      parameters: {
        market_type: config.marketType,
        depth: Number(config.depth) || 3,  // 确保是数字类型，与AgentConsolePractical.vue保持一致
        analysis_scopes: Array.from(config.analysisScopes || []),  // 确保是普通数组，不是Proxy
        analysts: Array.from(config.analysisScopes || []),  // 向后兼容
        llm_provider: config.llmProvider,
        llm_model: config.llmModel
      }
    }
    
    // Phase 2: 添加工具配置到参数中
    if (selectedTools.length > 0) {
      params.selected_tools = selectedTools
    }
    if (selectedDataSources.length > 0) {
      params.selected_data_sources = selectedDataSources
    }
    
    return params
  }
  
  /**
   * 获取市场的表单配置
   */
  async getFormConfigForMarket(marketType: MarketType): Promise<MarketFormConfig | null> {
    const marketConfig = await marketConfigAdapter.getMarketConfig(marketType)
    if (!marketConfig) {
      return null
    }
    
    const availableScopes = await this.getAnalysisScopes(marketType)
    
    return {
      hasTimeFrame: marketConfig.hasTimeFrame,
      hasDepthConfig: marketConfig.hasDepthConfig,
      availableScopes,
      defaultValues: {
        marketType,
        depth: marketConfig.defaultDepth,
        timeframe: marketConfig.defaultTimeFrame,
        analysisScopes: availableScopes.slice(0, 2).map(s => s.id)
      }
    }
  }
}

// 导出单例
export const analysisConfigAdapter = new AnalysisConfigAdapter()