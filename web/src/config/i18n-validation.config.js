/**
 * 翻译验证配置 - Linus原则：配置即代码，明确定义规则
 * 
 * "Good taste" - 这个配置文件定义了什么是好的翻译实践
 * 消除特殊情况，建立统一标准
 */

module.exports = {
  // 支持的语言列表
  supportedLanguages: [
    'zh-CN',  // 中文（简体）- 主要语言
    'en-US'   // 英语（美国）- 国际化语言
  ],
  
  // 默认语言（作为翻译完整性的基准）
  defaultLanguage: 'zh-CN',
  
  // 命名空间配置
  namespaces: {
    // 核心命名空间（必须100%翻译）
    core: {
      required: true,
      completionThreshold: 100,
      description: '核心功能翻译，必须完整'
    },
    
    // 通用命名空间
    common: {
      required: true,
      completionThreshold: 100,
      description: '通用组件和消息'
    },
    
    // 分析相关
    analysis: {
      required: true,
      completionThreshold: 95,
      description: '数据分析和图表相关'
    },
    
    // 用户界面
    ui: {
      required: true,
      completionThreshold: 90,
      description: '用户界面元素'
    },
    
    // 错误消息
    errors: {
      required: true,
      completionThreshold: 100,
      description: '错误和警告消息，必须完整'
    },
    
    // 帮助和文档
    help: {
      required: false,
      completionThreshold: 80,
      description: '帮助文档和提示信息'
    },
    
    // 营销内容
    marketing: {
      required: false,
      completionThreshold: 70,
      description: '营销和推广内容'
    }
  },
  
  // 验证规则
  validationRules: {
    // 键名规则
    keyNaming: {
      // 键名模式（小写字母、数字、下划线、点）
      pattern: /^[a-z0-9_.]+$/,
      maxDepth: 5,  // 最大嵌套深度
      description: '键名只能包含小写字母、数字、下划线和点'
    },
    
    // 值规则
    valueRules: {
      // 不允许空值
      noEmptyValues: true,
      // 不允许只有空格的值
      noWhitespaceOnly: true,
      // 最大长度（字符）
      maxLength: 1000,
      // 最小长度（字符）
      minLength: 1,
      description: '翻译值必须非空且有意义'
    },
    
    // 占位符规则
    placeholderRules: {
      // 占位符模式
      patterns: [
        /\{[a-zA-Z0-9_]+\}/g,  // {variable}
        /\{\{[a-zA-Z0-9_]+\}\}/g,  // {{variable}}
        /%[sd%]/g,  // %s, %d, %%
        /\$\{[a-zA-Z0-9_]+\}/g  // ${variable}
      ],
      // 要求所有语言的占位符保持一致
      consistentAcrossLanguages: true,
      description: '占位符必须在所有语言中保持一致'
    },
    
    // HTML标签规则
    htmlRules: {
      // 允许的HTML标签
      allowedTags: ['b', 'i', 'em', 'strong', 'br', 'span', 'a'],
      // 要求标签在所有语言中保持一致
      consistentTags: true,
      description: 'HTML标签必须正确闭合且在所有语言中一致'
    },
    
    // 特殊字符规则
    specialCharacters: {
      // 检查引号配对
      checkQuotePairs: true,
      // 检查括号配对
      checkBracketPairs: true,
      // 警告连续空格
      warnMultipleSpaces: true,
      description: '特殊字符必须正确配对'
    }
  },
  
  // 文件路径配置
  paths: {
    // 翻译文件根目录
    localesDir: 'src/locales',
    
    // 文件命名模式
    filePatterns: [
      '{language}/{namespace}.json',  // zh-CN/common.json
      '{namespace}.{language}.json',  // common.zh-CN.json
      '{language}-{namespace}.json'   // zh-CN-common.json
    ],
    
    // 输出目录
    outputDir: 'reports',
    
    description: '翻译文件的存储和组织规则'
  },
  
  // 报告配置
  reporting: {
    // 默认输出格式
    defaultFormat: 'text',
    
    // 支持的格式
    supportedFormats: ['text', 'json', 'html', 'csv'],
    
    // 详细程度
    verbosity: {
      errors: true,      // 显示错误
      warnings: true,    // 显示警告
      statistics: true,  // 显示统计信息
      suggestions: true  // 显示改进建议
    },
    
    // 错误分组
    groupBy: 'namespace',  // 'namespace', 'language', 'type'
    
    description: '验证报告的生成和格式化规则'
  },
  
  // 自动修复配置
  autoFix: {
    // 启用自动修复
    enabled: false,
    
    // 可自动修复的问题类型
    fixableIssues: [
      'trailing_whitespace',  // 尾随空格
      'multiple_spaces',      // 多余空格
      'empty_lines',          // 空行
      'json_formatting'       // JSON格式化
    ],
    
    // 备份原文件
    createBackup: true,
    
    description: '自动修复常见翻译问题'
  },
  
  // 性能配置
  performance: {
    // 最大文件大小（KB）
    maxFileSize: 100,
    
    // 最大键数量
    maxKeysPerFile: 1000,
    
    // 并发处理数
    concurrency: 4,
    
    // 缓存验证结果
    enableCache: true,
    
    description: '性能和资源使用限制'
  },
  
  // 集成配置
  integration: {
    // Git钩子
    gitHooks: {
      preCommit: true,   // 提交前验证
      prePush: false     // 推送前验证
    },
    
    // CI/CD集成
    cicd: {
      failOnErrors: true,     // 错误时失败
      failOnWarnings: false,  // 警告时不失败
      generateArtifacts: true // 生成报告文件
    },
    
    // IDE集成
    ide: {
      enableLinting: true,    // 启用IDE内联提示
      showWarnings: true,     // 显示警告
      autoComplete: true      // 自动补全
    },
    
    description: '与开发工具和流程的集成配置'
  },
  
  // 自定义规则
  customRules: [
    {
      name: 'no_hardcoded_urls',
      description: '检查是否包含硬编码的URL',
      pattern: /https?:\/\/[^\s]+/g,
      severity: 'warning',
      message: '翻译中不应包含硬编码的URL，请使用配置或变量'
    },
    
    {
      name: 'consistent_terminology',
      description: '检查术语一致性',
      terms: {
        'zh-CN': {
          'API': 'API',  // 保持英文
          '数据': '数据',
          '分析': '分析',
          '用户': '用户'
        },
        'en-US': {
          'API': 'API',
          'data': 'data',
          'analysis': 'analysis',
          'user': 'user'
        }
      },
      severity: 'warning',
      message: '请保持术语翻译的一致性'
    },
    
    {
      name: 'no_machine_translation_artifacts',
      description: '检查机器翻译痕迹',
      patterns: [
        /\b(的的|了了|在在)\b/g,  // 中文重复词
        /\b(a a|the the|and and)\b/gi,  // 英文重复词
        /[\u4e00-\u9fff]\s+[a-zA-Z]/g,  // 中英文间异常空格
      ],
      severity: 'error',
      message: '发现可能的机器翻译痕迹，请人工校对'
    }
  ],
  
  // 忽略规则
  ignore: {
    // 忽略的文件
    files: [
      '**/*.test.json',
      '**/*.spec.json',
      '**/temp/**'
    ],
    
    // 忽略的键
    keys: [
      'debug.*',
      'test.*',
      '*.internal.*'
    ],
    
    // 忽略的规则（按文件）
    rulesByFile: {
      'marketing/*.json': ['no_hardcoded_urls'],
      'help/*.json': ['consistent_terminology']
    },
    
    description: '验证时忽略的文件、键和规则'
  }
}