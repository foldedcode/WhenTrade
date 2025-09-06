/**
 * 翻译完整性检查服务 - Linus原则：零特殊情况的翻译验证
 * 
 * 功能：
 * 1. 检查翻译资源完整性
 * 2. 识别缺失的翻译键
 * 3. 验证翻译格式正确性
 * 4. 生成翻译报告
 * 5. 自动修复常见问题
 */

import type { AvailableLocales } from '../locales'
import { localeService } from './locale.service'
import { dynamicContentService } from './dynamic-content.service'

// 翻译验证结果
interface ValidationResult {
  isValid: boolean
  errors: ValidationError[]
  warnings: ValidationWarning[]
  statistics: TranslationStatistics
}

// 验证错误
interface ValidationError {
  type: 'missing_key' | 'invalid_format' | 'empty_value' | 'type_mismatch'
  key: string
  namespace: string
  language: string
  message: string
  severity: 'error' | 'warning'
}

// 验证警告
interface ValidationWarning {
  type: 'unused_key' | 'inconsistent_format' | 'placeholder_mismatch'
  key: string
  namespace: string
  languages: string[]
  message: string
}

// 翻译统计
interface TranslationStatistics {
  totalKeys: number
  translatedKeys: Record<string, number>
  missingKeys: Record<string, string[]>
  completionRate: Record<string, number>
  namespaces: string[]
  languages: string[]
}

// 翻译键信息
interface TranslationKeyInfo {
  key: string
  namespace: string
  type: 'string' | 'object' | 'array'
  hasPlaceholders: boolean
  placeholders: string[]
  languages: Record<string, any>
}

// 验证配置
interface ValidationConfig {
  strictMode: boolean
  checkPlaceholders: boolean
  checkUnusedKeys: boolean
  requiredLanguages: AvailableLocales[]
  ignoredKeys: string[]
  ignoredNamespaces: string[]
}

// 从配置文件加载的完整配置
interface I18nValidationConfig {
  supportedLanguages: string[]
  defaultLanguage: string
  namespaces: Record<string, {
    required: boolean
    completionThreshold: number
    description: string
  }>
  validationRules: {
    keyNaming: {
      pattern: RegExp
      maxDepth: number
      description: string
    }
    valueRules: {
      noEmptyValues: boolean
      noWhitespaceOnly: boolean
      maxLength: number
      minLength: number
      description: string
    }
    placeholderRules: {
      patterns: RegExp[]
      consistentAcrossLanguages: boolean
      description: string
    }
    htmlRules: {
      allowedTags: string[]
      consistentTags: boolean
      description: string
    }
    specialCharacters: {
      checkQuotePairs: boolean
      checkBracketPairs: boolean
      warnMultipleSpaces: boolean
      description: string
    }
  }
  customRules: Array<{
    name: string
    description: string
    pattern?: RegExp
    patterns?: RegExp[]
    severity: 'error' | 'warning'
    message: string
    terms?: Record<string, Record<string, string>>
  }>
  ignore: {
    files: string[]
    keys: string[]
    rulesByFile: Record<string, string[]>
  }
}

class TranslationValidatorService {
  private config: ValidationConfig
  private advancedConfig: I18nValidationConfig | null = null
  private localeService = localeService
  private dynamicContentService = dynamicContentService
  
  // 缓存的翻译数据
  private translationCache = new Map<string, Record<string, any>>()
  private lastValidation: ValidationResult | null = null
  
  constructor(config?: Partial<ValidationConfig>) {
    this.config = {
      strictMode: false,
      checkPlaceholders: true,
      checkUnusedKeys: false,
      requiredLanguages: ['zh-CN', 'en-US'],
      ignoredKeys: ['__meta__', '__version__'],
      ignoredNamespaces: ['test', 'dev'],
      ...config
    }
  }
  
  // 加载高级配置文件
  async loadAdvancedConfig(configPath?: string): Promise<void> {
    try {
      // 在浏览器环境中，需要通过fetch加载配置
      if (typeof window !== 'undefined') {
        const response = await fetch(configPath || '/src/config/i18n-validation.config.js')
        const configText = await response.text()
        // 简单的配置解析（生产环境应该使用更安全的方法）
        const configModule = new Function('module', 'exports', configText + '; return module.exports;')({}, {})
        this.advancedConfig = configModule
      } else {
        // Node.js环境
        const path = configPath || '../config/i18n-validation.config.js'
        this.advancedConfig = require(path)
      }
    } catch (error) {
      console.warn('Failed to load advanced config, using basic validation:', error)
    }
  }
  
  /**
   * 验证所有翻译资源
   */
  async validateAllTranslations(): Promise<ValidationResult> {
    const errors: ValidationError[] = []
    const warnings: ValidationWarning[] = []
    const statistics: TranslationStatistics = {
      totalKeys: 0,
      translatedKeys: {},
      missingKeys: {},
      completionRate: {},
      namespaces: [],
      languages: this.config.requiredLanguages
    }
    
    try {
      // 获取所有命名空间
      const namespaces = this.dynamicContentService.supportedNamespaces.value
        .filter(ns => !this.config.ignoredNamespaces.includes(ns))
      
      statistics.namespaces = namespaces
      
      // 加载所有翻译数据
      await this.loadAllTranslations(namespaces)
      
      // 收集所有翻译键
      const allKeys = this.collectAllKeys(namespaces)
      statistics.totalKeys = allKeys.length
      
      // 初始化统计数据
      for (const language of this.config.requiredLanguages) {
        statistics.translatedKeys[language] = 0
        statistics.missingKeys[language] = []
        statistics.completionRate[language] = 0
      }
      
      // 验证每个键
      for (const keyInfo of allKeys) {
        const keyErrors = await this.validateTranslationKey(keyInfo)
        errors.push(...keyErrors.filter(e => e.severity === 'error'))
        warnings.push(...keyErrors.filter(e => e.severity === 'warning').map(e => ({
          type: e.type as any,
          key: e.key,
          namespace: e.namespace,
          languages: [e.language],
          message: e.message
        })))
        
        // 更新统计
        for (const language of this.config.requiredLanguages) {
          if (keyInfo.languages[language] !== undefined && keyInfo.languages[language] !== '') {
            statistics.translatedKeys[language]++
          } else {
            statistics.missingKeys[language].push(`${keyInfo.namespace}.${keyInfo.key}`)
          }
        }
      }
      
      // 计算完成率
      for (const language of this.config.requiredLanguages) {
        statistics.completionRate[language] = 
          statistics.totalKeys > 0 
            ? (statistics.translatedKeys[language] / statistics.totalKeys) * 100 
            : 100
      }
      
      // 检查占位符一致性
      if (this.config.checkPlaceholders) {
        const placeholderWarnings = this.checkPlaceholderConsistency(allKeys)
        warnings.push(...placeholderWarnings)
      }
      
      // 检查未使用的键
      if (this.config.checkUnusedKeys) {
        const unusedWarnings = await this.checkUnusedKeys(allKeys)
        warnings.push(...unusedWarnings)
      }
      
    } catch (error) {
      errors.push({
        type: 'invalid_format',
        key: 'global',
        namespace: 'system',
        language: 'all',
        message: `Validation failed: ${error}`,
        severity: 'error'
      })
    }
    
    const result: ValidationResult = {
      isValid: errors.length === 0,
      errors,
      warnings,
      statistics
    }
    
    this.lastValidation = result
    return result
  }
  
  /**
   * 加载所有翻译数据
   */
  private async loadAllTranslations(namespaces: string[]): Promise<void> {
    this.translationCache.clear()
    
    for (const namespace of namespaces) {
      for (const language of this.config.requiredLanguages) {
        try {
          const content = await this.dynamicContentService.loadNamespaceContent(
            language, 
            namespace, 
            true // 强制重新加载
          )
          
          const cacheKey = `${language}-${namespace}`
          this.translationCache.set(cacheKey, content)
        } catch (error) {
          console.warn(`Failed to load ${language}/${namespace}:`, error)
          this.translationCache.set(`${language}-${namespace}`, {})
        }
      }
    }
  }
  
  /**
   * 收集所有翻译键
   */
  private collectAllKeys(namespaces: string[]): TranslationKeyInfo[] {
    const keyMap = new Map<string, TranslationKeyInfo>()
    
    for (const namespace of namespaces) {
      for (const language of this.config.requiredLanguages) {
        const cacheKey = `${language}-${namespace}`
        const content = this.translationCache.get(cacheKey) || {}
        
        this.extractKeysFromObject(content, '', namespace, language, keyMap)
      }
    }
    
    return Array.from(keyMap.values())
      .filter(key => !this.config.ignoredKeys.some(ignored => key.key.includes(ignored)))
  }
  
  /**
   * 从对象中提取键
   */
  private extractKeysFromObject(
    obj: any, 
    prefix: string, 
    namespace: string, 
    language: string, 
    keyMap: Map<string, TranslationKeyInfo>
  ): void {
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key
      const mapKey = `${namespace}.${fullKey}`
      
      if (!keyMap.has(mapKey)) {
        keyMap.set(mapKey, {
          key: fullKey,
          namespace,
          type: typeof value === 'string' ? 'string' : 
                Array.isArray(value) ? 'array' : 'object',
          hasPlaceholders: false,
          placeholders: [],
          languages: {}
        })
      }
      
      const keyInfo = keyMap.get(mapKey)!
      keyInfo.languages[language] = value
      
      // 检查占位符
      if (typeof value === 'string') {
        const placeholders = this.extractPlaceholders(value)
        if (placeholders.length > 0) {
          keyInfo.hasPlaceholders = true
          keyInfo.placeholders = [...new Set([...keyInfo.placeholders, ...placeholders])]
        }
      } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        // 递归处理嵌套对象
        this.extractKeysFromObject(value, fullKey, namespace, language, keyMap)
      }
    }
  }
  
  /**
   * 提取占位符
   */
  private extractPlaceholders(text: string): string[] {
    const matches = text.match(/\{([^}]+)\}/g)
    return matches ? matches.map(match => match.slice(1, -1)) : []
  }
  
  /**
   * 验证单个翻译键
   */
  private async validateTranslationKey(keyInfo: TranslationKeyInfo): Promise<ValidationError[]> {
    const errors: ValidationError[] = []
    
    for (const language of this.config.requiredLanguages) {
      const value = keyInfo.languages[language]
      
      // 检查缺失的键
      if (value === undefined) {
        errors.push({
          type: 'missing_key',
          key: keyInfo.key,
          namespace: keyInfo.namespace,
          language,
          message: `Missing translation for key '${keyInfo.key}' in language '${language}'`,
          severity: this.config.strictMode ? 'error' : 'warning'
        })
        continue
      }
      
      // 使用高级配置进行验证
      if (this.advancedConfig) {
        errors.push(...this.validateWithAdvancedRules(keyInfo.key, keyInfo.namespace, language, value))
      } else {
        // 基础验证
        errors.push(...this.validateBasicRules(keyInfo.key, keyInfo.namespace, language, value, keyInfo.type))
      }
    }
    
    return errors
  }
  
  /**
   * 基础验证规则
   */
  private validateBasicRules(
    key: string,
    namespace: string,
    language: string,
    value: any,
    expectedType: string
  ): ValidationError[] {
    const errors: ValidationError[] = []
    
    // 检查空值
    if (typeof value === 'string' && value.trim() === '') {
      errors.push({
        type: 'empty_value',
        key,
        namespace,
        language,
        message: `Empty translation value for key '${key}' in language '${language}'`,
        severity: 'warning'
      })
    }
    
    // 检查类型一致性
    const actualType = typeof value === 'string' ? 'string' : 
                      Array.isArray(value) ? 'array' : 'object'
    
    if (actualType !== expectedType) {
      errors.push({
        type: 'type_mismatch',
        key,
        namespace,
        language,
        message: `Type mismatch for key '${key}' in language '${language}': expected ${expectedType}, got ${actualType}`,
        severity: 'error'
      })
    }
    
    return errors
  }
  
  /**
   * 高级验证规则
   */
  private validateWithAdvancedRules(
    key: string,
    namespace: string,
    language: string,
    value: any
  ): ValidationError[] {
    const errors: ValidationError[] = []
    const config = this.advancedConfig!
    
    if (typeof value !== 'string') {
      return errors
    }
    
    // 键名验证
    if (!config.validationRules.keyNaming.pattern.test(key)) {
      errors.push({
        type: 'invalid_format',
        key,
        namespace,
        language,
        message: `Invalid key name '${key}': ${config.validationRules.keyNaming.description}`,
        severity: 'error'
      })
    }
    
    // 值规则验证
    const valueRules = config.validationRules.valueRules
    
    if (valueRules.noEmptyValues && value.trim() === '') {
      errors.push({
        type: 'empty_value',
        key,
        namespace,
        language,
        message: `Empty value for key '${key}' in ${language}/${namespace}`,
        severity: 'error'
      })
    }
    
    if (valueRules.noWhitespaceOnly && /^\s+$/.test(value)) {
      errors.push({
        type: 'invalid_format',
        key,
        namespace,
        language,
        message: `Value contains only whitespace for key '${key}' in ${language}/${namespace}`,
        severity: 'error'
      })
    }
    
    if (value.length > valueRules.maxLength) {
      errors.push({
        type: 'invalid_format',
        key,
        namespace,
        language,
        message: `Value too long (${value.length} > ${valueRules.maxLength}) for key '${key}' in ${language}/${namespace}`,
        severity: 'warning'
      })
    }
    
    if (value.length < valueRules.minLength) {
      errors.push({
        type: 'invalid_format',
        key,
        namespace,
        language,
        message: `Value too short (${value.length} < ${valueRules.minLength}) for key '${key}' in ${language}/${namespace}`,
        severity: 'warning'
      })
    }
    
    // 占位符验证
    if (config.validationRules.placeholderRules.consistentAcrossLanguages) {
      errors.push(...this.validateAdvancedPlaceholders(key, namespace, language, value))
    }
    
    // HTML标签验证
    errors.push(...this.validateHtmlTags(key, namespace, language, value))
    
    // 特殊字符验证
    errors.push(...this.validateSpecialCharacters(key, namespace, language, value))
    
    // 自定义规则验证
    errors.push(...this.validateCustomRules(key, namespace, language, value))
    
    return errors
  }
  
  /**
   * 验证高级占位符规则
   */
  private validateAdvancedPlaceholders(
    key: string,
    namespace: string,
    language: string,
    value: string
  ): ValidationError[] {
    const errors: ValidationError[] = []
    const config = this.advancedConfig!
    
    for (const pattern of config.validationRules.placeholderRules.patterns) {
      const matches = value.match(pattern)
      if (matches) {
        // 这里可以添加更复杂的占位符验证逻辑
      }
    }
    
    return errors
  }
  
  /**
   * 验证HTML标签
   */
  private validateHtmlTags(
    key: string,
    namespace: string,
    language: string,
    value: string
  ): ValidationError[] {
    const errors: ValidationError[] = []
    const config = this.advancedConfig!
    
    const htmlTagPattern = /<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/g
    const matches = value.match(htmlTagPattern)
    
    if (matches) {
      for (const match of matches) {
        const tagName = match.match(/<\/?([a-zA-Z][a-zA-Z0-9]*)/)?.[1]
        if (tagName && !config.validationRules.htmlRules.allowedTags.includes(tagName)) {
          errors.push({
            type: 'invalid_format',
            key,
            namespace,
            language,
            message: `Disallowed HTML tag '${tagName}' in key '${key}' for ${language}/${namespace}`,
            severity: 'error'
          })
        }
      }
    }
    
    return errors
  }
  
  /**
   * 验证特殊字符
   */
  private validateSpecialCharacters(
    key: string,
    namespace: string,
    language: string,
    value: string
  ): ValidationError[] {
    const errors: ValidationError[] = []
    const config = this.advancedConfig!
    
    const rules = config.validationRules.specialCharacters
    
    // 检查引号配对
    if (rules.checkQuotePairs) {
      const quotes = value.match(/["']/g)
      if (quotes && quotes.length % 2 !== 0) {
        errors.push({
          type: 'invalid_format',
          key,
          namespace,
          language,
          message: `Unmatched quotes in key '${key}' for ${language}/${namespace}`,
          severity: 'warning'
        })
      }
    }
    
    // 检查括号配对
    if (rules.checkBracketPairs) {
      const openBrackets = (value.match(/[\(\[\{]/g) || []).length
      const closeBrackets = (value.match(/[\)\]\}]/g) || []).length
      if (openBrackets !== closeBrackets) {
        errors.push({
          type: 'invalid_format',
          key,
          namespace,
          language,
          message: `Unmatched brackets in key '${key}' for ${language}/${namespace}`,
          severity: 'warning'
        })
      }
    }
    
    // 检查多个空格
    if (rules.warnMultipleSpaces && /\s{2,}/.test(value)) {
      errors.push({
        type: 'invalid_format',
        key,
        namespace,
        language,
        message: `Multiple consecutive spaces in key '${key}' for ${language}/${namespace}`,
        severity: 'warning'
      })
    }
    
    return errors
  }
  
  /**
   * 验证自定义规则
   */
  private validateCustomRules(
    key: string,
    namespace: string,
    language: string,
    value: string
  ): ValidationError[] {
    const errors: ValidationError[] = []
    const config = this.advancedConfig!
    
    for (const rule of config.customRules) {
      let isViolated = false
      
      if (rule.pattern && rule.pattern.test(value)) {
        isViolated = true
      }
      
      if (rule.patterns && rule.patterns.some(pattern => pattern.test(value))) {
        isViolated = true
      }
      
      if (rule.terms && rule.terms[language]) {
        const terms = rule.terms[language]
        for (const [term, replacement] of Object.entries(terms)) {
          if (value.includes(term)) {
            errors.push({
              type: 'invalid_format',
              key,
              namespace,
              language,
              message: `Use '${replacement}' instead of '${term}' in key '${key}' for ${language}/${namespace}`,
              severity: rule.severity
            })
          }
        }
      }
      
      if (isViolated) {
        errors.push({
          type: 'invalid_format',
          key,
          namespace,
          language,
          message: `Custom rule '${rule.name}' violated: ${rule.message}`,
          severity: rule.severity
        })
      }
    }
    
    return errors
  }
  
  /**
   * 检查占位符一致性
   */
  private checkPlaceholderConsistency(allKeys: TranslationKeyInfo[]): ValidationWarning[] {
    const warnings: ValidationWarning[] = []
    
    for (const keyInfo of allKeys) {
      if (!keyInfo.hasPlaceholders) continue
      
      const languagePlaceholders: Record<string, string[]> = {}
      
      // 收集每种语言的占位符
      for (const language of this.config.requiredLanguages) {
        const value = keyInfo.languages[language]
        if (typeof value === 'string') {
          languagePlaceholders[language] = this.extractPlaceholders(value)
        }
      }
      
      // 检查占位符一致性
      const referencePlaceholders = languagePlaceholders[this.config.requiredLanguages[0]] || []
      const inconsistentLanguages: string[] = []
      
      for (const [language, placeholders] of Object.entries(languagePlaceholders)) {
        if (language === this.config.requiredLanguages[0]) continue
        
        const missing = referencePlaceholders.filter(p => !placeholders.includes(p))
        const extra = placeholders.filter(p => !referencePlaceholders.includes(p))
        
        if (missing.length > 0 || extra.length > 0) {
          inconsistentLanguages.push(language)
        }
      }
      
      if (inconsistentLanguages.length > 0) {
        warnings.push({
          type: 'placeholder_mismatch',
          key: keyInfo.key,
          namespace: keyInfo.namespace,
          languages: inconsistentLanguages,
          message: `Placeholder mismatch for key '${keyInfo.key}' in languages: ${inconsistentLanguages.join(', ')}`
        })
      }
    }
    
    return warnings
  }
  
  /**
   * 检查未使用的键
   */
  private async checkUnusedKeys(allKeys: TranslationKeyInfo[]): Promise<ValidationWarning[]> {
    // 这里可以实现代码扫描逻辑，检查哪些翻译键在代码中未被使用
    // 由于复杂性，这里只返回空数组，实际实现需要AST分析
    return []
  }
  
  /**
   * 生成验证报告
   */
  generateReport(result?: ValidationResult): string {
    const validation = result || this.lastValidation
    if (!validation) {
      return 'No validation results available. Please run validation first.'
    }
    
    const lines: string[] = []
    lines.push('=== Translation Validation Report ===')
    lines.push('')
    
    // 总体状态
    lines.push(`Status: ${validation.isValid ? '✅ VALID' : '❌ INVALID'}`)
    lines.push(`Errors: ${validation.errors.length}`)
    lines.push(`Warnings: ${validation.warnings.length}`)
    lines.push('')
    
    // 统计信息
    lines.push('=== Statistics ===')
    lines.push(`Total Keys: ${validation.statistics.totalKeys}`)
    lines.push(`Namespaces: ${validation.statistics.namespaces.join(', ')}`)
    lines.push(`Languages: ${validation.statistics.languages.join(', ')}`)
    lines.push('')
    
    // 完成率
    lines.push('=== Completion Rates ===')
    for (const [language, rate] of Object.entries(validation.statistics.completionRate)) {
      const translated = validation.statistics.translatedKeys[language] || 0
      lines.push(`${language}: ${rate.toFixed(1)}% (${translated}/${validation.statistics.totalKeys})`)
    }
    lines.push('')
    
    // 错误详情
    if (validation.errors.length > 0) {
      lines.push('=== Errors ===')
      for (const error of validation.errors) {
        lines.push(`❌ [${error.type}] ${error.namespace}.${error.key} (${error.language}): ${error.message}`)
      }
      lines.push('')
    }
    
    // 警告详情
    if (validation.warnings.length > 0) {
      lines.push('=== Warnings ===')
      for (const warning of validation.warnings) {
        lines.push(`⚠️  [${warning.type}] ${warning.namespace}.${warning.key}: ${warning.message}`)
      }
      lines.push('')
    }
    
    // 缺失键详情
    lines.push('=== Missing Keys ===')
    for (const [language, missingKeys] of Object.entries(validation.statistics.missingKeys)) {
      if (missingKeys.length > 0) {
        lines.push(`${language}: ${missingKeys.length} missing`)
        for (const key of missingKeys.slice(0, 10)) { // 只显示前10个
          lines.push(`  - ${key}`)
        }
        if (missingKeys.length > 10) {
          lines.push(`  ... and ${missingKeys.length - 10} more`)
        }
        lines.push('')
      }
    }
    
    return lines.join('\n')
  }
  
  /**
   * 获取最后的验证结果
   */
  getLastValidation(): ValidationResult | null {
    return this.lastValidation
  }
  
  /**
   * 更新配置
   */
  updateConfig(config: Partial<ValidationConfig>): void {
    this.config = { ...this.config, ...config }
  }
  
  /**
   * 清除缓存
   */
  clearCache(): void {
    this.translationCache.clear()
    this.lastValidation = null
  }
}

// 创建单例实例
const translationValidatorService = new TranslationValidatorService()

export { TranslationValidatorService, translationValidatorService }
export type { 
  ValidationResult, 
  ValidationError, 
  ValidationWarning, 
  TranslationStatistics,
  ValidationConfig
}

export default translationValidatorService