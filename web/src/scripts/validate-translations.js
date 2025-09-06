#!/usr/bin/env node

/**
 * 翻译验证CLI工具 - Linus原则：简单直接的翻译检查
 * 
 * 用法：
 * node validate-translations.js [options]
 * 
 * 选项：
 * --strict         严格模式，将警告视为错误
 * --output <file>  输出报告到文件
 * --format <type>  输出格式：text, json, html
 * --fix            自动修复可修复的问题
 * --languages <langs> 指定要检查的语言，用逗号分隔
 * --namespaces <ns>   指定要检查的命名空间，用逗号分隔
 */

import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'
import { fileURLToPath } from 'url'
import { createRequire } from 'module'

// ES模块中的__dirname和__filename
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const require = createRequire(import.meta.url)

// 解析命令行参数
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    strict: false,
    output: null,
    format: 'text',
    fix: false,
    languages: ['zh-CN', 'en-US'],
    namespaces: null,
    help: false
  }
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    
    switch (arg) {
      case '--strict':
        options.strict = true
        break
      case '--output':
        options.output = args[++i]
        break
      case '--format':
        options.format = args[++i]
        break
      case '--fix':
        options.fix = true
        break
      case '--languages':
        options.languages = args[++i].split(',')
        break
      case '--namespaces':
        options.namespaces = args[++i].split(',')
        break
      case '--help':
      case '-h':
        options.help = true
        break
      default:
        console.error(`Unknown option: ${arg}`)
        process.exit(1)
    }
  }
  
  return options
}

// 显示帮助信息
function showHelp() {
  console.log(`
Translation Validation Tool

Usage: node validate-translations.js [options]

Options:
  --strict              Treat warnings as errors
  --output <file>       Output report to file
  --format <type>       Output format: text, json, html (default: text)
  --fix                 Auto-fix fixable issues
  --languages <langs>   Languages to check (comma-separated, default: zh-CN,en-US)
  --namespaces <ns>     Namespaces to check (comma-separated, default: all)
  --help, -h           Show this help message

Examples:
  node validate-translations.js
  node validate-translations.js --strict --output report.txt
  node validate-translations.js --format json --output report.json
  node validate-translations.js --languages zh-CN,en-US --namespaces common,analysis
`)
}

// 检查项目结构
function checkProjectStructure() {
  const requiredPaths = [
    'src/locales',
    'src/services/translation-validator.service.ts',
    'package.json'
  ]
  
  for (const requiredPath of requiredPaths) {
    if (!fs.existsSync(requiredPath)) {
      console.error(`❌ Required path not found: ${requiredPath}`)
      console.error('Please run this script from the web project root directory.')
      process.exit(1)
    }
  }
}

// 构建TypeScript文件
function buildTypeScript() {
  console.log('🔨 Building TypeScript files...')
  
  try {
    // 检查是否有TypeScript编译器
    execSync('npx tsc --version', { stdio: 'pipe' })
    
    // 编译TypeScript文件
    execSync('npx tsc --noEmit --skipLibCheck', { stdio: 'pipe' })
    console.log('✅ TypeScript compilation successful')
  } catch (error) {
    console.warn('⚠️  TypeScript compilation failed, continuing with validation...')
  }
}

// 加载翻译文件
function loadTranslationFiles(languages, namespaces) {
  const translations = {}
  const localesDir = path.join(process.cwd(), 'src/locales')
  
  // 如果没有指定命名空间，扫描所有可用的
  if (!namespaces) {
    namespaces = []
    const files = fs.readdirSync(localesDir)
    
    for (const file of files) {
      if (file.endsWith('.json') || file.endsWith('.js') || file.endsWith('.ts')) {
        const namespace = path.basename(file, path.extname(file))
        if (!namespaces.includes(namespace) && namespace !== 'index') {
          namespaces.push(namespace)
        }
      }
    }
    
    // 检查子目录
    for (const item of files) {
      const itemPath = path.join(localesDir, item)
      if (fs.statSync(itemPath).isDirectory()) {
        namespaces.push(item)
      }
    }
  }
  
  console.log(`📂 Loading translations for languages: ${languages.join(', ')}`)
  console.log(`📂 Loading translations for namespaces: ${namespaces.join(', ')}`)
  
  for (const language of languages) {
    translations[language] = {}
    
    for (const namespace of namespaces) {
      try {
        // 尝试不同的文件路径
        const possiblePaths = [
          path.join(localesDir, language, `${namespace}.json`),
          path.join(localesDir, `${language}-${namespace}.json`),
          path.join(localesDir, `${namespace}.${language}.json`),
          path.join(localesDir, namespace, `${language}.json`)
        ]
        
        let content = null
        for (const filePath of possiblePaths) {
          if (fs.existsSync(filePath)) {
            const fileContent = fs.readFileSync(filePath, 'utf8')
            content = JSON.parse(fileContent)
            break
          }
        }
        
        if (content) {
          translations[language][namespace] = content
        } else {
          console.warn(`⚠️  Translation file not found for ${language}/${namespace}`)
          translations[language][namespace] = {}
        }
      } catch (error) {
        console.error(`❌ Failed to load ${language}/${namespace}: ${error.message}`)
        translations[language][namespace] = {}
      }
    }
  }
  
  return { translations, namespaces }
}

// 加载验证配置
function loadValidationConfig() {
  try {
    const configPath = path.join(process.cwd(), 'src/config/i18n-validation.config.js')
    if (fs.existsSync(configPath)) {
      // 清除require缓存以获取最新配置
      delete require.cache[require.resolve(configPath)]
      return require(configPath)
    }
  } catch (error) {
    console.warn('⚠️  Failed to load validation config, using defaults:', error.message)
  }
  return null
}

// 验证翻译
function validateTranslations(translations, namespaces, options) {
  const errors = []
  const warnings = []
  const validationConfig = loadValidationConfig()
  
  const statistics = {
    totalKeys: 0,
    translatedKeys: {},
    missingKeys: {},
    completionRate: {},
    namespaces,
    languages: options.languages,
    configLoaded: !!validationConfig
  }
  
  // 初始化统计
  for (const language of options.languages) {
    statistics.translatedKeys[language] = 0
    statistics.missingKeys[language] = []
    statistics.completionRate[language] = 0
  }
  
  // 收集所有键
  const allKeys = new Set()
  
  function collectKeys(obj, prefix = '', namespace = '') {
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key
      const keyPath = namespace ? `${namespace}.${fullKey}` : fullKey
      
      if (typeof value === 'string') {
        allKeys.add(keyPath)
      } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        collectKeys(value, fullKey, namespace)
      }
    }
  }
  
  // 从所有语言和命名空间收集键
  for (const language of options.languages) {
    for (const namespace of namespaces) {
      if (translations[language] && translations[language][namespace]) {
        collectKeys(translations[language][namespace], '', namespace)
      }
    }
  }
  
  statistics.totalKeys = allKeys.size
  
  // 验证每个键
  for (const keyPath of allKeys) {
    const [namespace, ...keyParts] = keyPath.split('.')
    const key = keyParts.join('.')
    
    for (const language of options.languages) {
      const value = getNestedValue(translations[language]?.[namespace], key)
      
      if (value === undefined || value === null) {
        const error = {
          type: 'missing_key',
          key,
          namespace,
          language,
          message: `Missing translation for '${key}' in ${language}/${namespace}`,
          severity: options.strict ? 'error' : 'warning'
        }
        
        if (options.strict) {
          errors.push(error)
        } else {
          warnings.push(error)
        }
        
        statistics.missingKeys[language].push(keyPath)
      } else {
        // 使用高级配置进行验证
        if (validationConfig) {
          const validationErrors = validateKeyWithAdvancedRules(
            key, namespace, language, value, validationConfig, options.strict
          )
          
          for (const error of validationErrors) {
            if (error.severity === 'error') {
              errors.push(error)
            } else {
              warnings.push(error)
            }
          }
        } else {
          // 基础验证
          if (typeof value === 'string' && value.trim() === '') {
            warnings.push({
              type: 'empty_value',
              key,
              namespace,
              language,
              message: `Empty translation value for '${key}' in ${language}/${namespace}`,
              severity: 'warning'
            })
          }
        }
        
        if (typeof value === 'string' && value.trim() !== '') {
          statistics.translatedKeys[language]++
        }
      }
    }
  }
  
  // 计算完成率
  for (const language of options.languages) {
    statistics.completionRate[language] = 
      statistics.totalKeys > 0 
        ? (statistics.translatedKeys[language] / statistics.totalKeys) * 100 
        : 100
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    statistics
  }
}

// 获取嵌套值
function getNestedValue(obj, path) {
  if (!obj || !path) return undefined
  
  const keys = path.split('.')
  let current = obj
  
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key]
    } else {
      return undefined
    }
  }
  
  return current
}

// 使用高级规则验证单个键
function validateKeyWithAdvancedRules(key, namespace, language, value, config, strictMode) {
  const errors = []
  
  if (typeof value !== 'string') {
    return errors
  }
  
  // 键名验证
  if (config.validationRules && config.validationRules.keyNaming) {
    const keyPattern = new RegExp(config.validationRules.keyNaming.pattern.source)
    if (!keyPattern.test(key)) {
      errors.push({
        type: 'invalid_key_name',
        key,
        namespace,
        language,
        message: `Invalid key name '${key}': ${config.validationRules.keyNaming.description}`,
        severity: 'error'
      })
    }
  }
  
  // 值规则验证
  if (config.validationRules && config.validationRules.valueRules) {
    const valueRules = config.validationRules.valueRules
    
    if (valueRules.noEmptyValues && value.trim() === '') {
      errors.push({
        type: 'empty_value',
        key,
        namespace,
        language,
        message: `Empty value for key '${key}' in ${language}/${namespace}`,
        severity: strictMode ? 'error' : 'warning'
      })
    }
    
    if (valueRules.noWhitespaceOnly && /^\s+$/.test(value)) {
      errors.push({
        type: 'whitespace_only',
        key,
        namespace,
        language,
        message: `Value contains only whitespace for key '${key}' in ${language}/${namespace}`,
        severity: 'error'
      })
    }
    
    if (valueRules.maxLength && value.length > valueRules.maxLength) {
      errors.push({
        type: 'value_too_long',
        key,
        namespace,
        language,
        message: `Value too long (${value.length} > ${valueRules.maxLength}) for key '${key}' in ${language}/${namespace}`,
        severity: 'warning'
      })
    }
    
    if (valueRules.minLength && value.length < valueRules.minLength) {
      errors.push({
        type: 'value_too_short',
        key,
        namespace,
        language,
        message: `Value too short (${value.length} < ${valueRules.minLength}) for key '${key}' in ${language}/${namespace}`,
        severity: 'warning'
      })
    }
  }
  
  // HTML标签验证
  if (config.validationRules && config.validationRules.htmlRules) {
    const htmlTagPattern = /<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/g
    const matches = value.match(htmlTagPattern)
    
    if (matches) {
      for (const match of matches) {
        const tagName = match.match(/<\/?([a-zA-Z][a-zA-Z0-9]*)/)?.[1]
        if (tagName && !config.validationRules.htmlRules.allowedTags.includes(tagName)) {
          errors.push({
            type: 'disallowed_html_tag',
            key,
            namespace,
            language,
            message: `Disallowed HTML tag '${tagName}' in key '${key}' for ${language}/${namespace}`,
            severity: 'error'
          })
        }
      }
    }
  }
  
  // 特殊字符验证
  if (config.validationRules && config.validationRules.specialCharacters) {
    const rules = config.validationRules.specialCharacters
    
    // 检查引号配对
    if (rules.checkQuotePairs) {
      const quotes = value.match(/["']/g)
      if (quotes && quotes.length % 2 !== 0) {
        errors.push({
          type: 'unmatched_quotes',
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
          type: 'unmatched_brackets',
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
        type: 'multiple_spaces',
        key,
        namespace,
        language,
        message: `Multiple consecutive spaces in key '${key}' for ${language}/${namespace}`,
        severity: 'warning'
      })
    }
  }
  
  // 自定义规则验证
  if (config.customRules && Array.isArray(config.customRules)) {
    for (const rule of config.customRules) {
      let isViolated = false
      
      if (rule.pattern) {
        const pattern = new RegExp(rule.pattern.source, rule.pattern.flags)
        if (pattern.test(value)) {
          isViolated = true
        }
      }
      
      if (rule.patterns && Array.isArray(rule.patterns)) {
        for (const patternDef of rule.patterns) {
          const pattern = new RegExp(patternDef.source, patternDef.flags)
          if (pattern.test(value)) {
            isViolated = true
            break
          }
        }
      }
      
      if (rule.terms && rule.terms[language]) {
        const terms = rule.terms[language]
        for (const [term, replacement] of Object.entries(terms)) {
          if (value.includes(term)) {
            errors.push({
              type: 'terminology_inconsistency',
              key,
              namespace,
              language,
              message: `Use '${replacement}' instead of '${term}' in key '${key}' for ${language}/${namespace}`,
              severity: rule.severity || 'warning'
            })
          }
        }
      }
      
      if (isViolated) {
        errors.push({
          type: 'custom_rule_violation',
          key,
          namespace,
          language,
          message: `Custom rule '${rule.name}' violated: ${rule.message}`,
          severity: rule.severity || 'warning'
        })
      }
    }
  }
  
  return errors
}

// 生成报告
function generateReport(result, format) {
  switch (format) {
    case 'json':
      return JSON.stringify(result, null, 2)
    
    case 'html':
      return generateHtmlReport(result)
    
    case 'text':
    default:
      return generateTextReport(result)
  }
}

// 生成文本报告
function generateTextReport(result) {
  const lines = []
  lines.push('=== Translation Validation Report ===')
  lines.push('')
  
  // 状态
  lines.push(`Status: ${result.isValid ? '✅ VALID' : '❌ INVALID'}`)
  lines.push(`Errors: ${result.errors.length}`)
  lines.push(`Warnings: ${result.warnings.length}`)
  lines.push('')
  
  // 统计
  lines.push('=== Statistics ===')
  lines.push(`Total Keys: ${result.statistics.totalKeys}`)
  lines.push(`Namespaces: ${result.statistics.namespaces.join(', ')}`)
  lines.push(`Languages: ${result.statistics.languages.join(', ')}`)
  lines.push('')
  
  // 完成率
  lines.push('=== Completion Rates ===')
  for (const [language, rate] of Object.entries(result.statistics.completionRate)) {
    const translated = result.statistics.translatedKeys[language] || 0
    lines.push(`${language}: ${rate.toFixed(1)}% (${translated}/${result.statistics.totalKeys})`)
  }
  lines.push('')
  
  // 错误
  if (result.errors.length > 0) {
    lines.push('=== Errors ===')
    for (const error of result.errors) {
      lines.push(`❌ [${error.type}] ${error.namespace}.${error.key} (${error.language}): ${error.message}`)
    }
    lines.push('')
  }
  
  // 警告
  if (result.warnings.length > 0) {
    lines.push('=== Warnings ===')
    for (const warning of result.warnings) {
      lines.push(`⚠️  [${warning.type}] ${warning.namespace}.${warning.key} (${warning.language}): ${warning.message}`)
    }
    lines.push('')
  }
  
  return lines.join('\n')
}

// 生成HTML报告
function generateHtmlReport(result) {
  const status = result.isValid ? 'VALID' : 'INVALID'
  const statusColor = result.isValid ? '#28a745' : '#dc3545'
  
  return `
<!DOCTYPE html>
<html>
<head>
    <title>Translation Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f8f9fa; padding: 20px; border-radius: 5px; }
        .status { font-size: 24px; font-weight: bold; color: ${statusColor}; }
        .section { margin: 20px 0; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
        .success { color: #28a745; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Translation Validation Report</h1>
        <div class="status">Status: ${status}</div>
        <p>Errors: ${result.errors.length} | Warnings: ${result.warnings.length}</p>
    </div>
    
    <div class="section">
        <h2>Statistics</h2>
        <p>Total Keys: ${result.statistics.totalKeys}</p>
        <p>Namespaces: ${result.statistics.namespaces.join(', ')}</p>
        <p>Languages: ${result.statistics.languages.join(', ')}</p>
    </div>
    
    <div class="section">
        <h2>Completion Rates</h2>
        <table>
            <tr><th>Language</th><th>Completion Rate</th><th>Translated</th><th>Total</th></tr>
            ${Object.entries(result.statistics.completionRate).map(([lang, rate]) => {
              const translated = result.statistics.translatedKeys[lang] || 0
              return `<tr><td>${lang}</td><td>${rate.toFixed(1)}%</td><td>${translated}</td><td>${result.statistics.totalKeys}</td></tr>`
            }).join('')}
        </table>
    </div>
    
    ${result.errors.length > 0 ? `
    <div class="section">
        <h2 class="error">Errors</h2>
        <ul>
            ${result.errors.map(error => 
              `<li class="error">[${error.type}] ${error.namespace}.${error.key} (${error.language}): ${error.message}</li>`
            ).join('')}
        </ul>
    </div>
    ` : ''}
    
    ${result.warnings.length > 0 ? `
    <div class="section">
        <h2 class="warning">Warnings</h2>
        <ul>
            ${result.warnings.map(warning => 
              `<li class="warning">[${warning.type}] ${warning.namespace}.${warning.key} (${warning.language}): ${warning.message}</li>`
            ).join('')}
        </ul>
    </div>
    ` : ''}
</body>
</html>
`
}

// 主函数
function main() {
  const options = parseArgs()
  
  if (options.help) {
    showHelp()
    return
  }
  
  console.log('🔍 Starting translation validation...')
  
  // 检查项目结构
  checkProjectStructure()
  
  // 构建TypeScript（可选）
  buildTypeScript()
  
  // 加载翻译文件
  const { translations, namespaces } = loadTranslationFiles(options.languages, options.namespaces)
  
  // 验证翻译
  console.log('✅ Validating translations...')
  const result = validateTranslations(translations, namespaces, options)
  
  // 生成报告
  const report = generateReport(result, options.format)
  
  // 输出报告
  if (options.output) {
    fs.writeFileSync(options.output, report)
    console.log(`📄 Report saved to: ${options.output}`)
  } else {
    console.log('\n' + report)
  }
  
  // 退出状态
  if (!result.isValid) {
    console.error('\n❌ Translation validation failed!')
    process.exit(1)
  } else {
    console.log('\n✅ Translation validation passed!')
    process.exit(0)
  }
}

// 运行主函数 - ES模块检查
if (import.meta.url === `file://${process.argv[1]}`) {
  main()
}

// ES模块导出
export {
  validateTranslations,
  generateReport,
  loadTranslationFiles
}