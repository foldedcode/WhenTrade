/**
 * 语言环境服务 - Linus原则：统一的前后端语言管理
 * 
 * 功能：
 * 1. 与后端语言API集成
 * 2. 同步前后端语言状态
 * 3. 提供语言切换接口
 * 4. 管理本地语言偏好
 */

import { ref, computed } from 'vue'
import i18n, { saveLocale, type AvailableLocales } from '@/locales'
import { api } from '@/api'

// 语言响应接口
interface LanguageResponse {
  current_language: string
  supported_languages: string[]
  success: boolean
  message?: string
}

// 语言信息接口
interface LanguageInfo {
  current: string
  supported: string[]
  default: string
  fallback: string
}

class LocaleService {
  private _currentLanguage = ref<AvailableLocales>('zh-CN')
  private _supportedLanguages = ref<string[]>(['zh-CN', 'en-US'])
  private _isLoading = ref(false)
  private _lastSyncTime = ref<number>(0)
  
  constructor() {
    this.initializeFromLocal()
  }
  
  /**
   * 从本地存储初始化语言设置
   */
  private initializeFromLocal() {
    const saved = localStorage.getItem('when-trade-locale')
    if (saved && this.isValidLanguage(saved)) {
      this._currentLanguage.value = saved as AvailableLocales
      i18n.global.locale.value = saved as AvailableLocales
    }
  }
  
  /**
   * 验证语言代码是否有效
   */
  private isValidLanguage(lang: string): boolean {
    return ['zh-CN', 'en-US', 'zh', 'en'].includes(lang)
  }
  
  /**
   * 标准化语言代码
   */
  private normalizeLanguage(lang: string): AvailableLocales {
    const normalized = lang.toLowerCase()
    if (normalized.startsWith('zh')) return 'zh-CN'
    if (normalized.startsWith('en')) return 'en-US'
    return 'zh-CN' // 默认中文
  }
  
  /**
   * 获取当前语言
   */
  get currentLanguage(): AvailableLocales {
    return this._currentLanguage.value
  }
  
  /**
   * 获取支持的语言列表
   */
  get supportedLanguages(): string[] {
    return this._supportedLanguages.value
  }
  
  /**
   * 获取加载状态
   */
  get isLoading(): boolean {
    return this._isLoading.value
  }
  
  /**
   * 判断是否为中文
   */
  get isChinese(): boolean {
    return this._currentLanguage.value.startsWith('zh')
  }
  
  /**
   * 判断是否为英文
   */
  get isEnglish(): boolean {
    return this._currentLanguage.value.startsWith('en')
  }
  
  /**
   * 从后端同步语言设置
   */
  async syncFromBackend(): Promise<boolean> {
    try {
      this._isLoading.value = true
      
      const response = await api.get<LanguageResponse>('/api/v1/locale/current')
      
      if (response.data.success) {
        const backendLang = this.normalizeLanguage(response.data.current_language)
        
        // 如果后端语言与前端不一致，更新前端
        if (backendLang !== this._currentLanguage.value) {
          await this.setLanguage(backendLang, false) // 不同步到后端，避免循环
        }
        
        this._supportedLanguages.value = response.data.supported_languages
        this._lastSyncTime.value = Date.now()
        
        console.log(`Language synced from backend: ${backendLang}`)
        return true
      }
      
      return false
    } catch (error) {
      console.warn('Failed to sync language from backend:', error)
      return false
    } finally {
      this._isLoading.value = false
    }
  }
  
  /**
   * 设置语言
   */
  async setLanguage(language: AvailableLocales, syncToBackend: boolean = true): Promise<boolean> {
    try {
      this._isLoading.value = true
      
      const normalizedLang = this.normalizeLanguage(language)
      
      // 更新前端语言
      this._currentLanguage.value = normalizedLang
      i18n.global.locale.value = normalizedLang
      saveLocale(normalizedLang)
      
      // 同步到后端
      if (syncToBackend) {
        try {
          const response = await api.post<LanguageResponse>('/api/v1/locale/set', {
            language: normalizedLang
          })
          
          if (!response.data.success) {
            console.warn('Backend language sync failed:', response.data.message)
          } else {
            console.log(`Language synced to backend: ${normalizedLang}`)
          }
        } catch (error) {
          console.warn('Failed to sync language to backend:', error)
          // 前端语言切换成功，后端同步失败不影响用户体验
        }
      }
      
      console.log(`Language set to: ${normalizedLang}`)
      return true
      
    } catch (error) {
      console.error('Failed to set language:', error)
      return false
    } finally {
      this._isLoading.value = false
    }
  }
  
  /**
   * 切换语言（在支持的语言间循环）
   */
  async toggleLanguage(): Promise<boolean> {
    const currentIndex = this._supportedLanguages.value.indexOf(this._currentLanguage.value)
    const nextIndex = (currentIndex + 1) % this._supportedLanguages.value.length
    const nextLanguage = this._supportedLanguages.value[nextIndex] as AvailableLocales
    
    return await this.setLanguage(nextLanguage)
  }
  
  /**
   * 获取后端语言信息
   */
  async getLanguageInfo(): Promise<LanguageInfo | null> {
    try {
      const response = await api.get<LanguageInfo>('/api/v1/locale/info')
      return response.data
    } catch (error) {
      console.warn('Failed to get language info:', error)
      return null
    }
  }
  
  /**
   * 获取支持的语言列表（从后端）
   */
  async getSupportedLanguages(): Promise<string[]> {
    try {
      const response = await api.get<string[]>('/api/v1/locale/supported')
      this._supportedLanguages.value = response.data
      return response.data
    } catch (error) {
      console.warn('Failed to get supported languages:', error)
      return this._supportedLanguages.value
    }
  }
  
  /**
   * 检查语言环境健康状态
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await api.get('/api/v1/locale/health')
      return response.data.status === 'healthy'
    } catch (error) {
      console.warn('Language health check failed:', error)
      return false
    }
  }
  
  /**
   * 初始化语言服务（应用启动时调用）
   */
  async initialize(): Promise<void> {
    console.log('Initializing locale service...')
    
    // 1. 从后端获取支持的语言
    await this.getSupportedLanguages()
    
    // 2. 同步语言设置
    const syncSuccess = await this.syncFromBackend()
    
    if (!syncSuccess) {
      // 如果同步失败，将本地语言设置同步到后端
      await this.setLanguage(this._currentLanguage.value, true)
    }
    
    console.log(`Locale service initialized: ${this._currentLanguage.value}`)
  }
  
  /**
   * 获取响应式的语言状态
   */
  getReactiveState() {
    return {
      currentLanguage: computed(() => this._currentLanguage.value),
      supportedLanguages: computed(() => this._supportedLanguages.value),
      isLoading: computed(() => this._isLoading.value),
      isChinese: computed(() => this.isChinese),
      isEnglish: computed(() => this.isEnglish)
    }
  }
}

// 创建全局实例
export const localeService = new LocaleService()

// 导出便利函数
export const useLocale = () => {
  return {
    ...localeService.getReactiveState(),
    setLanguage: localeService.setLanguage.bind(localeService),
    toggleLanguage: localeService.toggleLanguage.bind(localeService),
    syncFromBackend: localeService.syncFromBackend.bind(localeService),
    initialize: localeService.initialize.bind(localeService)
  }
}

export default localeService