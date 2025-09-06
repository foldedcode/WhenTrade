/**
 * 主题管理 Composable
 * 支持专业模式（金色）和标准模式（蓝色）切换
 */

import { ref, computed, watch, onMounted, readonly, shallowRef } from 'vue'

export type ThemeMode = 'professional' | 'standard'
export type ColorScheme = 'dark' | 'light' | 'system'

interface ThemeConfig {
  mode: ThemeMode
  colorScheme: ColorScheme
}

// 本地存储键名
const THEME_STORAGE_KEY = 'when-trade-theme'

// 创建一个单例来存储主题状态
class ThemeManager {
  private static instance: ThemeManager
  public themeMode = ref<ThemeMode>('professional')
  public colorScheme = ref<ColorScheme>('dark')
  
  private constructor() {}
  
  static getInstance(): ThemeManager {
    if (!ThemeManager.instance) {
      ThemeManager.instance = new ThemeManager()
    }
    return ThemeManager.instance
  }
}

const themeManager = ThemeManager.getInstance()

export function useTheme() {
  // 使用单例中的响应式状态
  const themeMode = themeManager.themeMode
  const colorScheme = themeManager.colorScheme
  // 计算当前主题类名
  const themeClass = computed(() => {
    return `theme-${themeMode.value}`
  })

  // 计算当前配色方案类名
  const colorSchemeClass = computed(() => {
    if (colorScheme.value === 'system') {
      return 'theme-system'
    }
    return colorScheme.value
  })

  // 计算完整的主题类名
  const fullThemeClass = computed(() => {
    return `${themeClass.value} ${colorSchemeClass.value}`
  })

  // 切换主题模式
  const toggleThemeMode = () => {
    themeMode.value = themeMode.value === 'professional' ? 'standard' : 'professional'
    saveThemeConfig()
  }

  // 设置主题模式
  const setThemeMode = (mode: ThemeMode) => {
    themeMode.value = mode
    saveThemeConfig()
  }

  // 切换配色方案 - 简化逻辑，去掉system选项
  const toggleColorScheme = () => {
    // 直接在 dark 和 light 之间切换，去掉 system 选项
    colorScheme.value = colorScheme.value === 'dark' ? 'light' : 'dark'
    saveThemeConfig()
    applyTheme()
  }

  // 设置配色方案
  const setColorScheme = (scheme: ColorScheme) => {
    colorScheme.value = scheme
    saveThemeConfig()
  }

  // 保存主题配置到本地存储
  const saveThemeConfig = () => {
    const config: ThemeConfig = {
      mode: themeMode.value,
      colorScheme: colorScheme.value
    }
    localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(config))
  }

  // 从本地存储加载主题配置
  const loadThemeConfig = () => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY)
      if (stored) {
        // 尝试解析JSON
        const config: ThemeConfig = JSON.parse(stored)
        
        // 验证配置的有效性
        if (config && typeof config === 'object') {
          if (config.mode && ['professional', 'standard'].includes(config.mode)) {
            themeMode.value = config.mode
          }
          if (config.colorScheme && ['dark', 'light', 'system'].includes(config.colorScheme)) {
            colorScheme.value = config.colorScheme
          }
        }
      }
    } catch (error) {
      console.warn('Failed to load theme config:', error)
      // 清除无效的存储数据
      localStorage.removeItem(THEME_STORAGE_KEY)
      // 使用默认值
      themeMode.value = 'professional'
      colorScheme.value = 'dark'
    }
  }

  // 应用主题到DOM
  const applyTheme = () => {
    const html = document.documentElement
    
    // 移除旧的主题类
    html.classList.remove('theme-professional', 'theme-standard', 'dark', 'light', 'theme-system')
    
    // 应用新的主题类
    html.classList.add(themeClass.value)
    
    // 应用配色方案
    if (colorScheme.value === 'system') {
      html.classList.add('theme-system')
      // 系统主题跟随系统设置
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      html.classList.add(prefersDark ? 'dark' : 'light')
    } else {
      html.classList.add(colorScheme.value)
    }

    // 设置数据属性用于CSS选择器
    html.setAttribute('data-theme-mode', themeMode.value)
    html.setAttribute('data-color-scheme', colorScheme.value)
    
    // 设置 data-theme 属性以匹配 CSS
    if (colorScheme.value === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      html.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
    } else {
      html.setAttribute('data-theme', colorScheme.value)
    }
    
    // 触发自定义事件通知主题变化
    window.dispatchEvent(new CustomEvent('theme-changed', { 
      detail: { theme: colorScheme.value } 
    }))
  }

  // 监听系统主题变化
  const watchSystemTheme = () => {
    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      
      const handleChange = () => {
        if (colorScheme.value === 'system') {
          applyTheme()
        }
      }

      mediaQuery.addEventListener('change', handleChange)
      
      // 返回清理函数
      return () => {
        mediaQuery.removeEventListener('change', handleChange)
      }
    }
  }

  // 获取当前主题信息
  const getCurrentTheme = computed(() => ({
    mode: themeMode.value,
    colorScheme: colorScheme.value,
    isProfessional: themeMode.value === 'professional',
    isStandard: themeMode.value === 'standard',
    isDark: colorScheme.value === 'dark' || 
           (colorScheme.value === 'system' && 
            window.matchMedia('(prefers-color-scheme: dark)').matches),
    isLight: colorScheme.value === 'light' || 
            (colorScheme.value === 'system' && 
             !window.matchMedia('(prefers-color-scheme: dark)').matches),
    isSystem: colorScheme.value === 'system'
  }))

  // 获取主题颜色
  const getThemeColors = computed(() => {
    const isProfessional = themeMode.value === 'professional'
    
    return {
      primary: isProfessional ? '#d4af37' : '#3b82f6',
      primaryLight: isProfessional ? '#e6c547' : '#60a5fa',
      primaryDark: isProfessional ? '#b8941f' : '#2563eb',
      success: '#00c851',
      warning: '#ff6f00',
      error: '#d32f2f',
      info: '#1976d2'
    }
  })

  // 初始化主题
  const initTheme = () => {
    loadThemeConfig()
    applyTheme()
    // 不再监听系统主题，因为我们移除了 system 选项
  }

  // 监听主题变化并立即应用
  watch([themeMode, colorScheme], () => {
    applyTheme()
  }, { immediate: false })

  // 组件挂载时初始化 - 确保只初始化一次
  let isInitialized = false
  onMounted(() => {
    if (!isInitialized) {
      initTheme()
      isInitialized = true
    }
  })

  return {
    // 状态
    themeMode: readonly(themeMode),
    colorScheme: readonly(colorScheme),
    
    // 计算属性
    themeClass,
    colorSchemeClass,
    fullThemeClass,
    getCurrentTheme,
    getThemeColors,
    
    // 方法
    toggleThemeMode,
    setThemeMode,
    toggleColorScheme,
    setColorScheme,
    initTheme,
    applyTheme
  }
}

// 导出类型
export type { ThemeConfig }