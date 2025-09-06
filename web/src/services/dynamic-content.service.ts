/**
 * 动态语言内容加载服务 - Linus原则：零特殊情况的前端内容加载
 * 
 * 功能：
 * 1. 运行时动态加载语言资源
 * 2. 支持内容热更新和缓存管理
 * 3. 与后端API集成获取动态内容
 * 4. 统一的回退机制
 */

import { ref, computed, watch } from 'vue'
import type { Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { localeService } from './locale.service'
import { i18nFormatterService, type FormatOptions, type FormatParams } from './i18n-formatter.service'

// 内容缓存项接口
interface ContentCacheItem {
  content: Record<string, any>
  loadedAt: number
  ttl: number
  namespace: string
  language: string
}

// 动态内容加载配置
interface DynamicContentConfig {
  cacheTtlMs: number
  enableHotReload: boolean
  fallbackLanguage: string
  apiEndpoint: string
}

// 内容加载状态
interface LoadingState {
  isLoading: boolean
  error: string | null
  lastUpdated: number | null
}

class DynamicContentService {
  private cache = new Map<string, ContentCacheItem>()
  private loadingStates = new Map<string, LoadingState>()
  private config: DynamicContentConfig
  private localeService = localeService
  private i18n: any
  
  // 响应式状态
  private _isInitialized = ref(false)
  private _currentLanguage = ref('zh-CN')
  private _supportedNamespaces = ref<string[]>(['common', 'analysis', 'history', 'settings'])
  
  constructor(config?: Partial<DynamicContentConfig>) {
    this.config = {
      cacheTtlMs: 5 * 60 * 1000, // 5分钟
      enableHotReload: true,
      fallbackLanguage: 'en-US',
      apiEndpoint: '/api/v1/locale',
      ...config
    }
    
    // localeService已经初始化
    this.i18n = useI18n()
    
    this.initialize()
  }
  
  // 公共响应式属性
  get isInitialized(): Ref<boolean> {
    return this._isInitialized
  }
  
  get currentLanguage(): Ref<string> {
    return this._currentLanguage
  }
  
  get supportedNamespaces(): Ref<string[]> {
    return this._supportedNamespaces
  }
  
  /**
   * 初始化服务
   */
  private async initialize(): Promise<void> {
    try {
      // 初始化语言服务
      await this.localeService.initialize()
      
      // 设置当前语言
      this._currentLanguage.value = this.localeService.currentLanguage
      
      // 监听语言变化
      watch(
        () => this.localeService.currentLanguage,
        (newLanguage) => {
          this._currentLanguage.value = newLanguage
          this.onLanguageChanged(newLanguage)
        }
      )
      
      // 预加载核心命名空间
      await this.preloadCoreNamespaces()
      
      this._isInitialized.value = true
      console.log('DynamicContentService initialized')
      
    } catch (error) {
      console.error('Failed to initialize DynamicContentService:', error)
      throw error
    }
  }
  
  /**
   * 预加载核心命名空间
   */
  private async preloadCoreNamespaces(): Promise<void> {
    const language = this._currentLanguage.value
    const coreNamespaces = ['common', 'analysis']
    
    const loadPromises = coreNamespaces.map(namespace => 
      this.loadNamespaceContent(language, namespace)
    )
    
    await Promise.allSettled(loadPromises)
  }
  
  /**
   * 语言变化处理
   */
  private async onLanguageChanged(newLanguage: string): Promise<void> {
    console.log(`Language changed to: ${newLanguage}`)
    
    // 清除旧语言的缓存
    this.clearLanguageCache(this._currentLanguage.value)
    
    // 预加载新语言的核心内容
    await this.preloadCoreNamespaces()
    
    // 更新Vue i18n
    if (this.i18n && this.i18n.locale) {
      this.i18n.locale.value = newLanguage
    }
  }
  
  /**
   * 生成缓存键
   */
  private getCacheKey(language: string, namespace: string): string {
    return `${language}_${namespace}`
  }
  
  /**
   * 检查缓存是否有效
   */
  private isCacheValid(cacheItem: ContentCacheItem): boolean {
    const now = Date.now()
    return (now - cacheItem.loadedAt) < cacheItem.ttl
  }
  
  /**
   * 从本地文件加载内容
   */
  private async loadFromLocalFile(language: string, namespace: string): Promise<Record<string, any>> {
    try {
      // 动态导入语言文件
      const module = await import(`../locales/${language}/${namespace}.json`)
      return module.default || module
    } catch (error) {
      console.warn(`Failed to load local file for ${language}/${namespace}:`, error)
      return {}
    }
  }
  
  /**
   * 从API加载内容
   */
  private async loadFromApi(language: string, namespace: string): Promise<Record<string, any>> {
    try {
      const response = await fetch(`${this.config.apiEndpoint}/content/${language}/${namespace}`)
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`)
      }
      
      const data = await response.json()
      return data.content || {}
      
    } catch (error) {
      console.warn(`Failed to load from API for ${language}/${namespace}:`, error)
      return {}
    }
  }
  
  /**
   * 加载命名空间内容
   */
  async loadNamespaceContent(
    language: string, 
    namespace: string, 
    forceReload: boolean = false
  ): Promise<Record<string, any>> {
    const cacheKey = this.getCacheKey(language, namespace)
    
    // 检查缓存
    if (!forceReload && this.cache.has(cacheKey)) {
      const cacheItem = this.cache.get(cacheKey)!
      if (this.isCacheValid(cacheItem)) {
        console.debug(`Cache hit: ${cacheKey}`)
        return cacheItem.content
      }
    }
    
    // 检查加载状态
    const loadingState = this.loadingStates.get(cacheKey)
    if (loadingState?.isLoading) {
      // 等待正在进行的加载
      return new Promise((resolve) => {
        const checkInterval = setInterval(() => {
          const state = this.loadingStates.get(cacheKey)
          if (!state?.isLoading) {
            clearInterval(checkInterval)
            const cacheItem = this.cache.get(cacheKey)
            resolve(cacheItem?.content || {})
          }
        }, 100)
      })
    }
    
    // 设置加载状态
    this.loadingStates.set(cacheKey, {
      isLoading: true,
      error: null,
      lastUpdated: null
    })
    
    try {
      let content: Record<string, any> = {}
      
      // 优先从本地文件加载
      content = await this.loadFromLocalFile(language, namespace)
      
      // 如果本地文件为空，尝试从API加载
      if (Object.keys(content).length === 0) {
        content = await this.loadFromApi(language, namespace)
      }
      
      // 更新缓存
      const cacheItem: ContentCacheItem = {
        content,
        loadedAt: Date.now(),
        ttl: this.config.cacheTtlMs,
        namespace,
        language
      }
      
      this.cache.set(cacheKey, cacheItem)
      
      // 更新加载状态
      this.loadingStates.set(cacheKey, {
        isLoading: false,
        error: null,
        lastUpdated: Date.now()
      })
      
      console.debug(`Loaded namespace: ${cacheKey}`)
      return content
      
    } catch (error) {
      console.error(`Failed to load namespace ${cacheKey}:`, error)
      
      // 更新错误状态
      this.loadingStates.set(cacheKey, {
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        lastUpdated: Date.now()
      })
      
      return {}
    }
  }
  
  /**
   * 获取本地化消息
   */
  async getMessage(
    key: string, 
    language?: string, 
    namespace: string = 'common',
    params?: Record<string, any>,
    formatOptions?: FormatOptions
  ): Promise<string> {
    // 确定语言
    const targetLanguage = language || this._currentLanguage.value
    
    // 获取内容
    const content = await this.loadNamespaceContent(targetLanguage, namespace)
    
    // 查找消息
    let message = content[key]
    
    if (message === undefined) {
      // 尝试回退语言
      if (targetLanguage !== this.config.fallbackLanguage) {
        console.debug(`Message key '${key}' not found in ${targetLanguage}, trying fallback`)
        return this.getMessage(key, this.config.fallbackLanguage, namespace, params, formatOptions)
      } else {
        // 最后的回退：返回键名
        console.warn(`Message key '${key}' not found in any language`)
        message = key
      }
    }
    
    // 格式化消息
    if (params && typeof message === 'string') {
      try {
        return this.formatMessage(message, params, formatOptions)
      } catch (error) {
        console.warn(`Failed to format message '${key}':`, error)
        return message
      }
    }
    
    return String(message)
  }
  
  /**
   * 获取嵌套消息
   */
  async getNestedMessage(
    keyPath: string, 
    language?: string, 
    namespace: string = 'common',
    params?: Record<string, any>,
    formatOptions?: FormatOptions
  ): Promise<string> {
    // 确定语言
    const targetLanguage = language || this._currentLanguage.value
    
    // 获取内容
    const content = await this.loadNamespaceContent(targetLanguage, namespace)
    
    // 按路径查找
    const keys = keyPath.split('.')
    let current: any = content
    
    for (const key of keys) {
      if (current && typeof current === 'object' && key in current) {
        current = current[key]
      } else {
        // 尝试回退语言
        if (targetLanguage !== this.config.fallbackLanguage) {
          return this.getNestedMessage(keyPath, this.config.fallbackLanguage, namespace, params, formatOptions)
        } else {
          console.warn(`Nested key path '${keyPath}' not found`)
          return keyPath
        }
      }
    }
    
    // 格式化消息
    const message = String(current)
    if (params) {
      try {
        return this.formatMessage(message, params, formatOptions)
      } catch (error) {
        console.warn(`Failed to format nested message '${keyPath}':`, error)
        return message
      }
    }
    
    return message
  }
  
  /**
   * 格式化消息
   */
  private formatMessage(
    template: string, 
    params: Record<string, any>, 
    formatOptions?: FormatOptions
  ): string {
    // 使用增强的格式化服务
    return i18nFormatterService.formatMessage(
      template, 
      params as FormatParams, 
      formatOptions,
      this._currentLanguage.value as any
    )
  }
  
  /**
   * 重新加载命名空间
   */
  async reloadNamespace(language: string, namespace: string): Promise<boolean> {
    try {
      await this.loadNamespaceContent(language, namespace, true)
      console.log(`Reloaded namespace: ${language}/${namespace}`)
      return true
    } catch (error) {
      console.error(`Failed to reload namespace ${language}/${namespace}:`, error)
      return false
    }
  }
  
  /**
   * 清除语言缓存
   */
  clearLanguageCache(language: string): void {
    const keysToDelete: string[] = []
    
    for (const [key, cacheItem] of this.cache.entries()) {
      if (cacheItem.language === language) {
        keysToDelete.push(key)
      }
    }
    
    keysToDelete.forEach(key => {
      this.cache.delete(key)
      this.loadingStates.delete(key)
    })
    
    console.log(`Cleared cache for language: ${language}`)
  }
  
  /**
   * 清除所有缓存
   */
  clearAllCache(): void {
    this.cache.clear()
    this.loadingStates.clear()
    console.log('All cache cleared')
  }
  
  /**
   * 获取缓存统计
   */
  getCacheStats(): {
    totalItems: number
    validItems: number
    invalidItems: number
    cacheKeys: string[]
    loadingStates: Record<string, LoadingState>
  } {
    const now = Date.now()
    let validItems = 0
    
    for (const cacheItem of this.cache.values()) {
      if (this.isCacheValid(cacheItem)) {
        validItems++
      }
    }
    
    const loadingStatesObj: Record<string, LoadingState> = {}
    for (const [key, state] of this.loadingStates.entries()) {
      loadingStatesObj[key] = state
    }
    
    return {
      totalItems: this.cache.size,
      validItems,
      invalidItems: this.cache.size - validItems,
      cacheKeys: Array.from(this.cache.keys()),
      loadingStates: loadingStatesObj
    }
  }
  
  /**
   * 设置语言
   */
  async setLanguage(language: string): Promise<void> {
    // 将string转换为AvailableLocales类型
    const normalizedLang = language as any // 临时类型断言
    await this.localeService.setLanguage(normalizedLang)
  }
  
  /**
   * 获取支持的语言列表
   */
  async getSupportedLanguages(): Promise<string[]> {
    return this.localeService.getSupportedLanguages()
  }
}

// 创建全局实例
const dynamicContentService = new DynamicContentService()

// 导出服务和便利函数
export { DynamicContentService, dynamicContentService }

// 便利函数
export const getDynamicMessage = (
  key: string, 
  language?: string, 
  namespace?: string,
  params?: Record<string, any>,
  formatOptions?: FormatOptions
): Promise<string> => {
  return dynamicContentService.getMessage(key, language, namespace, params, formatOptions)
}

export const getNestedMessage = (
  keyPath: string, 
  language?: string, 
  namespace?: string,
  params?: Record<string, any>,
  formatOptions?: FormatOptions
): Promise<string> => {
  return dynamicContentService.getNestedMessage(keyPath, language, namespace, params, formatOptions)
}

export const reloadContent = (language: string, namespace: string): Promise<boolean> => {
  return dynamicContentService.reloadNamespace(language, namespace)
}

export const clearContentCache = (language?: string): void => {
  if (language) {
    dynamicContentService.clearLanguageCache(language)
  } else {
    dynamicContentService.clearAllCache()
  }
}

export default dynamicContentService