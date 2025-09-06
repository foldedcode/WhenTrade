/**
 * 国际化格式化服务 - Linus原则：零特殊情况的多语言格式化
 * 
 * 功能：
 * 1. 支持复数形式处理
 * 2. 日期时间本地化格式化
 * 3. 数字和货币格式化
 * 4. 变量插值和模板处理
 * 5. 性别化语言支持
 */

import type { AvailableLocales } from '../locales'
import { localeService } from './locale.service'

// 复数规则类型
type PluralRule = 'zero' | 'one' | 'two' | 'few' | 'many' | 'other'

// 格式化选项
interface FormatOptions {
  // 数字格式化
  numberFormat?: Intl.NumberFormatOptions
  // 日期格式化
  dateFormat?: Intl.DateTimeFormatOptions
  // 货币格式化
  currencyFormat?: {
    currency: string
    options?: Intl.NumberFormatOptions
  }
  // 复数处理
  pluralRules?: Partial<Record<PluralRule, string>>
  // 性别化
  gender?: 'male' | 'female' | 'neutral'
}

// 格式化参数
interface FormatParams {
  [key: string]: any
  count?: number
  date?: Date | string | number
  number?: number
  currency?: number
  gender?: 'male' | 'female' | 'neutral'
}

class I18nFormatterService {
  private localeService = localeService
  
  // 复数规则缓存
  private pluralRulesCache = new Map<string, Intl.PluralRules>()
  
  // 数字格式化器缓存
  private numberFormatCache = new Map<string, Intl.NumberFormat>()
  
  // 日期格式化器缓存
  private dateFormatCache = new Map<string, Intl.DateTimeFormat>()
  
  /**
   * 获取复数规则
   */
  private getPluralRules(locale: string): Intl.PluralRules {
    if (!this.pluralRulesCache.has(locale)) {
      this.pluralRulesCache.set(locale, new Intl.PluralRules(locale))
    }
    return this.pluralRulesCache.get(locale)!
  }
  
  /**
   * 获取数字格式化器
   */
  private getNumberFormat(locale: string, options?: Intl.NumberFormatOptions): Intl.NumberFormat {
    const key = `${locale}-${JSON.stringify(options || {})}`
    if (!this.numberFormatCache.has(key)) {
      this.numberFormatCache.set(key, new Intl.NumberFormat(locale, options))
    }
    return this.numberFormatCache.get(key)!
  }
  
  /**
   * 获取日期格式化器
   */
  private getDateFormat(locale: string, options?: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
    const key = `${locale}-${JSON.stringify(options || {})}`
    if (!this.dateFormatCache.has(key)) {
      this.dateFormatCache.set(key, new Intl.DateTimeFormat(locale, options))
    }
    return this.dateFormatCache.get(key)!
  }
  
  /**
   * 处理复数形式
   */
  private handlePlural(
    template: string, 
    count: number, 
    locale: string, 
    pluralRules?: Partial<Record<PluralRule, string>>
  ): string {
    if (!pluralRules) {
      return template
    }
    
    const rules = this.getPluralRules(locale)
    const rule = rules.select(count) as PluralRule
    
    // 优先使用提供的复数规则
    if (pluralRules[rule]) {
      return pluralRules[rule]
    }
    
    // 回退到 'other' 规则
    if (pluralRules.other) {
      return pluralRules.other
    }
    
    return template
  }
  
  /**
   * 格式化数字
   */
  private formatNumber(
    value: number, 
    locale: string, 
    options?: Intl.NumberFormatOptions
  ): string {
    const formatter = this.getNumberFormat(locale, options)
    return formatter.format(value)
  }
  
  /**
   * 格式化日期
   */
  private formatDate(
    value: Date | string | number, 
    locale: string, 
    options?: Intl.DateTimeFormatOptions
  ): string {
    const date = value instanceof Date ? value : new Date(value)
    const formatter = this.getDateFormat(locale, options)
    return formatter.format(date)
  }
  
  /**
   * 格式化货币
   */
  private formatCurrency(
    value: number, 
    locale: string, 
    currency: string, 
    options?: Intl.NumberFormatOptions
  ): string {
    const currencyOptions: Intl.NumberFormatOptions = {
      style: 'currency',
      currency,
      ...options
    }
    return this.formatNumber(value, locale, currencyOptions)
  }
  
  /**
   * 处理性别化语言
   */
  private handleGender(
    template: string, 
    gender: 'male' | 'female' | 'neutral' = 'neutral'
  ): string {
    // 处理性别化标记 {gender:male/female/neutral}
    return template.replace(/\{gender:([^}]+)\}/g, (match, genderOptions) => {
      const options = genderOptions.split('/')
      switch (gender) {
        case 'male':
          return options[0] || ''
        case 'female':
          return options[1] || options[0] || ''
        case 'neutral':
        default:
          return options[2] || options[0] || ''
      }
    })
  }
  
  /**
   * 主要格式化方法
   */
  formatMessage(
    template: string, 
    params: FormatParams = {}, 
    options: FormatOptions = {},
    locale?: AvailableLocales
  ): string {
    const currentLocale = locale || this.localeService.currentLanguage
    let result = template
    
    // 1. 处理复数形式
    if (typeof params.count === 'number' && options.pluralRules) {
      result = this.handlePlural(result, params.count, currentLocale, options.pluralRules)
    }
    
    // 2. 处理性别化
    if (params.gender || options.gender) {
      result = this.handleGender(result, params.gender || options.gender)
    }
    
    // 3. 处理变量插值
    result = result.replace(/\{([^}]+)\}/g, (match, key) => {
      const value = params[key]
      
      if (value === undefined) {
        return match
      }
      
      // 特殊格式化处理
      if (key === 'date' && params.date) {
        return this.formatDate(params.date, currentLocale, options.dateFormat)
      }
      
      if (key === 'number' && typeof params.number === 'number') {
        return this.formatNumber(params.number, currentLocale, options.numberFormat)
      }
      
      if (key === 'currency' && typeof params.currency === 'number' && options.currencyFormat) {
        return this.formatCurrency(
          params.currency, 
          currentLocale, 
          options.currencyFormat.currency,
          options.currencyFormat.options
        )
      }
      
      // 数字类型的自动格式化
      if (typeof value === 'number') {
        return this.formatNumber(value, currentLocale)
      }
      
      // 日期类型的自动格式化
      if (value instanceof Date) {
        return this.formatDate(value, currentLocale)
      }
      
      return String(value)
    })
    
    return result
  }
  
  /**
   * 格式化复数消息的便捷方法
   */
  formatPlural(
    templates: Partial<Record<PluralRule, string>>,
    count: number,
    params: FormatParams = {},
    locale?: AvailableLocales
  ): string {
    const currentLocale = locale || this.localeService.currentLanguage
    const rules = this.getPluralRules(currentLocale)
    const rule = rules.select(count) as PluralRule
    
    const template = templates[rule] || templates.other || ''
    
    return this.formatMessage(template, { ...params, count }, {}, locale)
  }
  
  /**
   * 格式化日期的便捷方法
   */
  formatDateOnly(
    date: Date | string | number,
    options?: Intl.DateTimeFormatOptions,
    locale?: AvailableLocales
  ): string {
    const currentLocale = locale || this.localeService.currentLanguage
    return this.formatDate(date, currentLocale, options)
  }
  
  /**
   * 格式化数字的便捷方法
   */
  formatNumberOnly(
    number: number,
    options?: Intl.NumberFormatOptions,
    locale?: AvailableLocales
  ): string {
    const currentLocale = locale || this.localeService.currentLanguage
    return this.formatNumber(number, currentLocale, options)
  }
  
  /**
   * 格式化货币的便捷方法
   */
  formatCurrencyOnly(
    amount: number,
    currency: string,
    options?: Intl.NumberFormatOptions,
    locale?: AvailableLocales
  ): string {
    const currentLocale = locale || this.localeService.currentLanguage
    return this.formatCurrency(amount, currentLocale, currency, options)
  }
  
  /**
   * 清除缓存
   */
  clearCache(): void {
    this.pluralRulesCache.clear()
    this.numberFormatCache.clear()
    this.dateFormatCache.clear()
  }
  
  /**
   * 获取缓存统计
   */
  getCacheStats(): {
    pluralRules: number
    numberFormats: number
    dateFormats: number
  } {
    return {
      pluralRules: this.pluralRulesCache.size,
      numberFormats: this.numberFormatCache.size,
      dateFormats: this.dateFormatCache.size
    }
  }
}

// 创建单例实例
const i18nFormatterService = new I18nFormatterService()

export { I18nFormatterService, i18nFormatterService }
export type { FormatOptions, FormatParams, PluralRule }

// 便捷导出函数
export const formatMessage = (
  template: string, 
  params?: FormatParams, 
  options?: FormatOptions,
  locale?: AvailableLocales
): string => {
  return i18nFormatterService.formatMessage(template, params, options, locale)
}

export const formatPlural = (
  templates: Partial<Record<PluralRule, string>>,
  count: number,
  params?: FormatParams,
  locale?: AvailableLocales
): string => {
  return i18nFormatterService.formatPlural(templates, count, params, locale)
}

export const formatDate = (
  date: Date | string | number,
  options?: Intl.DateTimeFormatOptions,
  locale?: AvailableLocales
): string => {
  return i18nFormatterService.formatDateOnly(date, options, locale)
}

export const formatNumber = (
  number: number,
  options?: Intl.NumberFormatOptions,
  locale?: AvailableLocales
): string => {
  return i18nFormatterService.formatNumberOnly(number, options, locale)
}

export const formatCurrency = (
  amount: number,
  currency: string,
  options?: Intl.NumberFormatOptions,
  locale?: AvailableLocales
): string => {
  return i18nFormatterService.formatCurrencyOnly(amount, currency, options, locale)
}

export default i18nFormatterService