import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import enUS from './en-US'

// 类型定义
export type MessageSchema = typeof zhCN

// 获取浏览器语言
function getBrowserLocale(): string {
  const browserLang = navigator.language.toLowerCase()
  
  // 标准化语言代码
  if (browserLang.startsWith('zh')) {
    return 'zh-CN'
  } else if (browserLang.startsWith('en')) {
    return 'en-US'
  }
  
  return 'zh-CN' // 默认中文
}

// 标准化语言代码
function normalizeLocale(locale: string): string {
  const lowerLocale = locale.toLowerCase()
  if (lowerLocale === 'zh' || lowerLocale.startsWith('zh')) {
    return 'zh-CN'
  } else if (lowerLocale === 'en' || lowerLocale.startsWith('en')) {
    return 'en-US'
  }
  return 'zh-CN' // 默认中文
}

// 获取保存的语言偏好
function getSavedLocale(): string {
  const saved = localStorage.getItem('when-trade-locale')
  return saved ? normalizeLocale(saved) : getBrowserLocale()
}

// 保存语言偏好
export function saveLocale(locale: string): void {
  localStorage.setItem('when-trade-locale', normalizeLocale(locale))
}

// 创建 i18n 实例
const i18n = createI18n<[MessageSchema], 'zh-CN' | 'en-US'>({
  legacy: false,
  locale: getSavedLocale(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  },
  // 设置 fallback 策略
  fallbackWarn: false,
  missingWarn: false
})

// 手动添加别名 - 在创建实例后
if (i18n.global.messages.value) {
  // 确保别名指向相同的对象引用
  (i18n.global.messages.value as any)['zh'] = zhCN;
  (i18n.global.messages.value as any)['en'] = enUS;
}

export default i18n

// 导出类型
export type AvailableLocales = 'zh-CN' | 'en-US'

// 支持的语言列表
export const supportedLocales: Array<{
  code: AvailableLocales
  name: string
  flag: string
}> = [
  { code: 'zh-CN', name: '中文', flag: '🇨🇳' },
  { code: 'en-US', name: 'English', flag: '🇺🇸' }
] 