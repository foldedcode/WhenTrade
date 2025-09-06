/**
 * LLM提供商自动检测和模型获取服务
 * 基于环境变量API key自动检测可用的LLM提供商，并动态获取模型列表
 */

import { createI18n } from 'vue-i18n'

// 导入翻译文件
import zhProviders from '@/locales/zh-CN/providers.json'
import enProviders from '@/locales/en-US/providers.json'

// 创建专用的 i18n 实例
const providerI18n = createI18n({
  locale: localStorage.getItem('when-trade-locale') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  missingWarn: false, // 禁用缺失翻译警告
  fallbackWarn: false, // 禁用fallback警告
  messages: {
    'zh-CN': { providers: zhProviders },
    'zh': { providers: zhProviders },
    'en-US': { providers: enProviders },
    'en': { providers: enProviders }
  }
})

// 类型定义
export interface LLMProvider {
  id: string
  name: string
  description: string
  logo: string
  apiKeyEnvName: string
  available: boolean
  models: LLMModel[]
  baseUrl?: string
}

export interface LLMModel {
  id: string
  name: string
  description: string
  contextWindow: number
  pricing?: {
    input: number    // per 1K tokens
    output: number   // per 1K tokens
  }
  capabilities: string[]
  recommended?: boolean
}

// 获取翻译文本的辅助函数
const getProviderTranslation = (providerId: string, key: 'name' | 'description'): string => {
  try {
    const locale = localStorage.getItem('when-trade-locale') || 'zh-CN'
    // 动态更新i18n实例的locale
    providerI18n.global.locale = locale as 'zh-CN' | 'en-US'
    const t = providerI18n.global.t
    const translationKey = `providers.${providerId}.${key}`
    const result = t(translationKey) as string
    
    // 如果翻译键不存在，返回键本身，避免返回英文fallback
    if (result === translationKey) {
      // 提供基本的fallback描述
      const fallbackDescriptions: Record<string, Record<'name' | 'description', string>> = {
        openai: { name: 'OpenAI', description: '领先的AI研究公司，GPT系列模型' },
        google: { name: 'Google', description: 'Google AI服务，Gemini模型' },
        deepseek: { name: 'DeepSeek', description: 'DeepSeek AI，高性价比推理模型' },
        kimi: { name: 'Moonshot Kimi', description: '月之暗面，超长上下文模型' }
      }
      
      if (locale === 'en-US') {
        const enFallbacks: Record<string, Record<'name' | 'description', string>> = {
          openai: { name: 'OpenAI', description: 'Leading AI research company, GPT models' },
          google: { name: 'Google', description: 'Google AI services, Gemini models' },
          deepseek: { name: 'DeepSeek', description: 'DeepSeek AI, cost-effective reasoning models' },
          kimi: { name: 'Moonshot Kimi', description: 'Moonshot AI, ultra-long context models' }
        }
        return enFallbacks[providerId]?.[key] || fallbackDescriptions[providerId]?.[key] || result
      }
      
      return fallbackDescriptions[providerId]?.[key] || result
    }
    
    return result
  } catch (error) {
    console.warn(`获取提供商翻译失败: ${providerId}.${key}`, error)
    // 返回基本信息
    return providerId
  }
}

// 获取模型描述翻译的辅助函数
const getModelTranslation = (providerId: string, modelId: string): string => {
  const locale = localStorage.getItem('when-trade-locale') || 'zh-CN'
  
  // 直接从翻译数据中获取，避免触发Vue i18n的fallback机制
  const isEnglish = locale.startsWith('en')
  const providers = isEnglish ? enProviders : zhProviders
  
  const modelTranslation = providers[providerId as keyof typeof providers]?.models?.[modelId as any]
  return modelTranslation || modelId
}

// LLM提供商配置
const LLM_PROVIDERS_CONFIG: Record<string, Omit<LLMProvider, 'available' | 'models' | 'description'> & { getDescription: () => string }> = {
  openai: {
    id: 'openai',
    name: 'OpenAI',
    logo: 'openai',
    apiKeyEnvName: 'OPENAI_API_KEY',
    baseUrl: 'https://api.openai.com/v1',
    getDescription: () => getProviderTranslation('openai', 'description')
  },
  google: {
    id: 'google',
    name: 'Google',
    logo: 'google',
    apiKeyEnvName: 'GOOGLE_API_KEY',
    baseUrl: 'https://generativelanguage.googleapis.com/v1',
    getDescription: () => getProviderTranslation('google', 'description')
  },
  deepseek: {
    id: 'deepseek',
    name: 'DeepSeek',
    logo: 'deepseek',
    apiKeyEnvName: 'DEEPSEEK_API_KEY',
    baseUrl: 'https://api.deepseek.com/v1',
    getDescription: () => getProviderTranslation('deepseek', 'description')
  },
  kimi: {
    id: 'kimi',
    name: 'Moonshot Kimi',
    logo: 'kimi',
    apiKeyEnvName: 'KIMI_API_KEY',
    baseUrl: 'https://api.moonshot.cn/v1',
    getDescription: () => getProviderTranslation('kimi', 'description')
  }
}

// 默认模型配置生成函数（当API调用失败时使用）
const getDefaultModels = (): Record<string, LLMModel[]> => {
  return {
  openai: [
    {
      id: 'gpt-4o',
      name: 'GPT-4o',
      description: getModelTranslation('openai', 'gpt-4o'),
      contextWindow: 128000,
      pricing: { input: 0.005, output: 0.015 },
      capabilities: ['文本生成', '代码生成', '分析推理', '多模态'],
      recommended: true
    },
    {
      id: 'gpt-4o-mini',
      name: 'GPT-4o Mini',
      description: getModelTranslation('openai', 'gpt-4o-mini'),
      contextWindow: 128000,
      pricing: { input: 0.00015, output: 0.0006 },
      capabilities: ['文本生成', '代码生成', '快速分析']
    },
    {
      id: 'gpt-4-turbo',
      name: 'GPT-4 Turbo',
      description: getModelTranslation('openai', 'gpt-4-turbo'),
      contextWindow: 128000,
      pricing: { input: 0.01, output: 0.03 },
      capabilities: ['文本生成', '代码生成', '分析推理']
    }
  ],
  google: [
    {
      id: 'gemini-1.5-pro',
      name: 'Gemini 1.5 Pro',
      description: getModelTranslation('google', 'gemini-1.5-pro'),
      contextWindow: 1048576,
      pricing: { input: 0.00125, output: 0.005 },
      capabilities: ['文本生成', '多模态', '分析推理', '超长文本'],
      recommended: true
    },
    {
      id: 'gemini-1.5-flash',
      name: 'Gemini 1.5 Flash',
      description: getModelTranslation('google', 'gemini-1.5-flash'),
      contextWindow: 1048576,
      pricing: { input: 0.00025, output: 0.001 },
      capabilities: ['文本生成', '快速分析', '多模态']
    }
  ],
  deepseek: [
    {
      id: 'deepseek-chat',
      name: 'DeepSeek Chat',
      description: getModelTranslation('deepseek', 'deepseek-chat'),
      contextWindow: 32768,
      pricing: { input: 0.0014, output: 0.0028 },
      capabilities: ['文本生成', '代码生成', '分析推理'],
      recommended: true
    },
    {
      id: 'deepseek-coder',
      name: 'DeepSeek Coder',
      description: getModelTranslation('deepseek', 'deepseek-coder'),
      contextWindow: 16384,
      pricing: { input: 0.0014, output: 0.0028 },
      capabilities: ['代码生成', '代码分析', '技术文档']
    }
  ],
  kimi: [
    {
      id: 'moonshot-v1-8k',
      name: 'Moonshot v1 8K',
      description: getModelTranslation('kimi', 'moonshot-v1-8k'),
      contextWindow: 8192,
      pricing: { input: 0.012, output: 0.012 },
      capabilities: ['文本生成', '对话', '分析']
    },
    {
      id: 'moonshot-v1-32k',
      name: 'Moonshot v1 32K',
      description: getModelTranslation('kimi', 'moonshot-v1-32k'),
      contextWindow: 32768,
      pricing: { input: 0.024, output: 0.024 },
      capabilities: ['文本生成', '长文本', '分析']
    },
    {
      id: 'moonshot-v1-128k',
      name: 'Moonshot v1 128K',
      description: getModelTranslation('kimi', 'moonshot-v1-128k'),
      contextWindow: 131072,
      pricing: { input: 0.06, output: 0.06 },
      capabilities: ['文本生成', '超长文本', '深度分析'],
      recommended: true
    }
  ]
  }
}

export class LLMDetectionService {
  private static instance: LLMDetectionService
  private providers: LLMProvider[] = []
  private initialized = false

  static getInstance(): LLMDetectionService {
    if (!this.instance) {
      this.instance = new LLMDetectionService()
    }
    return this.instance
  }

  /**
   * 初始化LLM检测服务
   * 检测环境变量中的API key，确定可用的提供商
   */
  async initialize(): Promise<void> {
    if (this.initialized) return

    // console.log('🔍 开始检测可用的LLM提供商...')

    // 通过后端API检测环境变量中的API key
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/llm/providers`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const responseData = await response.json()
        // 修复：正确提取available字段
        const availableProviders = responseData.available || {}
        this.providers = await this.buildProvidersList(availableProviders)
      } else {
        // 后端不可用时的降级处理
        console.warn('⚠️ 后端LLM检测API不可用，使用本地检测')
        this.providers = await this.fallbackDetection()
      }
    } catch (error) {
      console.warn('⚠️ LLM检测失败，使用默认配置:', error)
      this.providers = await this.fallbackDetection()
    }

    this.initialized = true
    // console.log('✅ LLM检测完成，可用提供商:', this.providers.map(p => p.name))
  }

  /**
   * 获取所有可用的LLM提供商
   */
  async getAvailableProviders(): Promise<LLMProvider[]> {
    if (!this.initialized) {
      await this.initialize()
    }
    return this.providers.filter(p => p.available)
  }

  /**
   * 获取指定提供商的模型列表
   */
  async getModelsForProvider(providerId: string): Promise<LLMModel[]> {
    const provider = this.providers.find(p => p.id === providerId)
    if (!provider || !provider.available) {
      return []
    }

    // 如果已有模型数据，直接返回
    if (provider.models && provider.models.length > 0) {
      return provider.models
    }

    // 动态获取模型列表
    try {
      const models = await this.fetchModelsFromAPI(providerId)
      provider.models = models
      return models
    } catch (error) {
      console.warn(`⚠️ 无法获取${provider.name}的模型列表，使用默认配置:`, error)
      const defaultModels = getDefaultModels()[providerId] || []
      provider.models = defaultModels
      return defaultModels
    }
  }

  /**
   * 获取推荐的默认配置
   */
  async getRecommendedConfig(): Promise<{ providerId: string; modelId: string } | null> {
    const providers = await this.getAvailableProviders()
    
    // 优先级：Kimi > DeepSeek > OpenAI > Google
    const priorityOrder = ['kimi', 'deepseek', 'openai', 'google']
    
    for (const providerId of priorityOrder) {
      const provider = providers.find(p => p.id === providerId)
      if (provider) {
        const models = await this.getModelsForProvider(providerId)
        const recommendedModel = models.find(m => m.recommended) || models[0]
        
        if (recommendedModel) {
          return {
            providerId,
            modelId: recommendedModel.id
          }
        }
      }
    }

    return null
  }

  /**
   * 构建提供商列表
   */
  private async buildProvidersList(availableProviders: Record<string, boolean>): Promise<LLMProvider[]> {
    const providers: LLMProvider[] = []

    for (const [providerId, config] of Object.entries(LLM_PROVIDERS_CONFIG)) {
      const available = availableProviders[providerId] || false
      
      providers.push({
        id: config.id,
        name: config.name,
        description: config.getDescription(), // 使用动态翻译
        logo: config.logo,
        apiKeyEnvName: config.apiKeyEnvName,
        baseUrl: config.baseUrl,
        available,
        models: available ? getDefaultModels()[providerId] || [] : []
      })
    }

    return providers
  }

  /**
   * 降级检测（当后端不可用时）
   */
  private async fallbackDetection(): Promise<LLMProvider[]> {
    // 在前端无法直接访问环境变量，所以假设所有提供商都可用
    // 实际使用时会在调用API时验证
    return Object.entries(LLM_PROVIDERS_CONFIG).map(([providerId, config]) => ({
      id: config.id,
      name: config.name,
      description: config.getDescription(), // 使用动态翻译
      logo: config.logo,
      apiKeyEnvName: config.apiKeyEnvName,
      baseUrl: config.baseUrl,
      available: true, // 乐观假设
      models: getDefaultModels()[providerId] || []
    }))
  }

  /**
   * 从API动态获取模型列表
   */
  private async fetchModelsFromAPI(providerId: string): Promise<LLMModel[]> {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/llm/providers/${providerId}/models`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const models = await response.json()
        return models.map((model: any) => ({
          id: model.id,
          name: model.name || model.id,
          description: model.description || `${providerId}模型`,
          contextWindow: model.context_length || 4096,
          pricing: model.pricing ? {
            input: model.pricing.prompt,
            output: model.pricing.completion
          } : undefined,
          capabilities: model.capabilities || ['文本生成'],
          recommended: model.recommended || false
        }))
      }
    } catch (error) {
      console.warn(`获取${providerId}模型列表失败:`, error)
    }

    // 返回默认配置
    return getDefaultModels()[providerId] || []
  }
}

// 导出单例实例
export const llmDetectionService = LLMDetectionService.getInstance()

// 便捷函数
export async function getAvailableLLMProviders(): Promise<LLMProvider[]> {
  return await llmDetectionService.getAvailableProviders()
}

export async function getModelsForProvider(providerId: string): Promise<LLMModel[]> {
  return await llmDetectionService.getModelsForProvider(providerId)
}

export async function getRecommendedLLMConfig(): Promise<{ providerId: string; modelId: string } | null> {
  return await llmDetectionService.getRecommendedConfig()
}