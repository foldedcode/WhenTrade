/**
 * 专业金融终端主题系统
 * 支持专业模式（金色）和标准模式（蓝色）切换
 */

export type ColorMode = 'professional' | 'standard' | 'success' | 'tech' | 'alert' | 'cyan' | 'orange'
export type ThemeMode = 'dark' | 'light'

export interface ThemeConfig {
  colorMode: ColorMode
  themeMode: ThemeMode
}

/**
 * 获取当前颜色模式
 */
export function getCurrentColorMode(): ColorMode {
  const root = document.documentElement
  return root.hasAttribute('data-color-mode') 
    ? root.getAttribute('data-color-mode') as ColorMode
    : 'professional'
}

/**
 * 设置颜色模式
 */
export function setColorMode(mode: ColorMode): void {
  const root = document.documentElement
  root.setAttribute('data-color-mode', mode)
  
  // 更新CSS变量
  const isProfessional = mode === 'professional'
  root.style.setProperty('--current-theme-mode', `'${mode}'`)
  
  // 触发自定义事件通知组件更新
  window.dispatchEvent(new CustomEvent('colorModeChange', { 
    detail: { mode } 
  }))
  
  // 保存到localStorage
  localStorage.setItem('when-trade-color-mode', mode)
}

/**
 * 获取当前主题模式
 */
export function getCurrentThemeMode(): ThemeMode {
  const root = document.documentElement
  return root.hasAttribute('data-theme')
    ? root.getAttribute('data-theme') as ThemeMode
    : 'dark'
}

/**
 * 设置主题模式
 */
export function setThemeMode(mode: ThemeMode): void {
  const root = document.documentElement
  root.setAttribute('data-theme', mode)
  
  // 保存到localStorage
  localStorage.setItem('when-trade-theme-mode', mode)
}

/**
 * 初始化主题系统
 */
export function initializeTheme(): ThemeConfig {
  // 从localStorage恢复设置
  const savedColorMode = localStorage.getItem('when-trade-color-mode') as ColorMode
  const savedThemeMode = localStorage.getItem('when-trade-theme-mode') as ThemeMode
  
  const colorMode = savedColorMode || 'professional'
  const themeMode = savedThemeMode || 'dark'
  
  // 只设置DOM属性，不触发事件（避免与ColorSchemeSwitcher冲突）
  document.documentElement.setAttribute('data-color-mode', colorMode)
  document.documentElement.setAttribute('data-theme', themeMode)
  
  return { colorMode, themeMode }
}

/**
 * 切换颜色模式
 */
export function toggleColorMode(): ColorMode {
  const current = getCurrentColorMode()
  const newMode = current === 'professional' ? 'standard' : 'professional'
  setColorMode(newMode)
  return newMode
}

/**
 * 切换主题模式 - 直接切换，不做防抖处理
 */
export function toggleThemeMode(): ThemeMode {
  const current = getCurrentThemeMode()
  const newMode = current === 'dark' ? 'light' : 'dark'
  
  // 直接设置属性和保存，确保立即生效
  const root = document.documentElement
  root.setAttribute('data-theme', newMode)
  localStorage.setItem('when-trade-theme-mode', newMode)
  
  // 触发自定义事件
  window.dispatchEvent(new CustomEvent('theme-changed', { 
    detail: { theme: newMode } 
  }))
  
  return newMode
}

/**
 * 获取当前主题配置
 */
export function getCurrentThemeConfig(): ThemeConfig {
  return {
    colorMode: getCurrentColorMode(),
    themeMode: getCurrentThemeMode()
  }
}

/**
 * 获取主题相关的CSS类名
 */
export function getThemeClasses(): string[] {
  const config = getCurrentThemeConfig()
  return [
    `color-mode-${config.colorMode}`,
    `theme-mode-${config.themeMode}`
  ]
}

/**
 * 检查颜色对比度是否符合WCAG标准
 */
export function checkColorContrast(foreground: string, background: string): {
  ratio: number
  wcagAA: boolean
  wcagAAA: boolean
} {
  // 简化的对比度计算 - 实际项目中应使用更精确的算法
  const getLuminance = (color: string): number => {
    // 这里应该实现完整的相对亮度计算
    // 为了简化，返回一个估算值
    const hex = color.replace('#', '')
    const r = parseInt(hex.substr(0, 2), 16) / 255
    const g = parseInt(hex.substr(2, 2), 16) / 255
    const b = parseInt(hex.substr(4, 2), 16) / 255
    
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  
  const l1 = getLuminance(foreground)
  const l2 = getLuminance(background)
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
  
  return {
    ratio,
    wcagAA: ratio >= 4.5,
    wcagAAA: ratio >= 7
  }
}

/**
 * 验证当前主题的可访问性
 */
export function validateThemeAccessibility(): {
  isValid: boolean
  issues: string[]
} {
  const issues: string[] = []
  
  // 检查主要颜色组合的对比度
  const primaryColor = getCurrentColorMode() === 'professional' ? '#d4af37' : '#3b82f6'
  const backgroundColor = '#1e1e1e'
  const textColor = '#ffffff'
  
  const primaryContrast = checkColorContrast(primaryColor, backgroundColor)
  const textContrast = checkColorContrast(textColor, backgroundColor)
  
  if (!primaryContrast.wcagAA) {
    issues.push(`主色与背景色对比度不足: ${primaryContrast.ratio.toFixed(2)}`)
  }
  
  if (!textContrast.wcagAA) {
    issues.push(`文字与背景色对比度不足: ${textContrast.ratio.toFixed(2)}`)
  }
  
  return {
    isValid: issues.length === 0,
    issues
  }
}