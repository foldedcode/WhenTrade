/**
 * LLM提供商Logo配置系统
 * 使用 Simple Icons CDN 提供彩色品牌图标
 */

export interface LogoConfig {
  /** 浅色主题Logo路径 */
  light?: string
  /** 深色主题Logo路径 */
  dark?: string
  /** 彩色Logo路径（优先使用） */
  color?: string
  /** 回退Logo路径 */
  fallback?: string
  /** 提供商显示名称 */
  name: string
  /** 提供商描述 */
  description?: string
  /** 官方网站 */
  website?: string
  /** 是否为主要提供商 */
  isPrimary?: boolean
  /** 支持的模型列表 */
  models?: string[]
  /** 别名列表 */
  aliases?: string[]
}

export interface LogoProviderMap {
  [key: string]: LogoConfig
}

/**
 * Simple Icons CDN 基础 URL - 使用彩色 SVG 图标
 */
const SIMPLE_ICONS_CDN = 'https://cdn.simpleicons.org'

/**
 * 生成 Simple Icons URL
 * @param slug - 图标的 slug 名称
 * @param theme - 主题类型，用于确定颜色
 */
function getSimpleIconUrl(slug: string, theme: 'light' | 'dark' | 'color' = 'dark'): string {
  if (theme === 'color') {
    // 使用彩色SVG图标
    return `${SIMPLE_ICONS_CDN}/${slug}`
  }
  // 黑白图标：深色主题用白色，浅色主题用黑色
  const color = theme === 'dark' ? 'ffffff' : '000000'
  return `${SIMPLE_ICONS_CDN}/${slug}/${color}`
}

/**
 * 生成占位符图标
 */
function generatePlaceholderIcon(name: string, theme: 'light' | 'dark' = 'dark'): string {
  const firstLetter = name.charAt(0).toUpperCase()
  const bgColor = theme === 'dark' ? '#ffffff' : '#000000'
  const textColor = theme === 'dark' ? '#000000' : '#ffffff'
  
  // 使用 encodeURIComponent 处理 Unicode 字符
  const svgContent = `
    <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="40" rx="8" fill="${bgColor}"/>
      <text x="50%" y="50%" text-anchor="middle" dy="0.35em" fill="${textColor}" font-size="20" font-weight="600">
        ${firstLetter}
      </text>
    </svg>
  `
  
  // 使用 encodeURIComponent 代替 btoa 来处理 Unicode
  const svg = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgContent.trim())}`
  return svg
}

/**
 * LLM提供商Logo配置映射
 */
export const logoProviderMap: LogoProviderMap = {
  // === OpenAI 系列 ===
  'openai': {
    color: getSimpleIconUrl('openai', 'color'),
    light: getSimpleIconUrl('openai', 'light'),
    dark: getSimpleIconUrl('openai', 'dark'),
    name: 'OpenAI',
    description: 'AI研究',
    website: 'https://openai.com',
    isPrimary: true,
    models: ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4o'],
    aliases: ['gpt', 'chatgpt']
  },
  'gpt': {
    color: getSimpleIconUrl('openai', 'color'),
    light: getSimpleIconUrl('openai', 'light'),
    dark: getSimpleIconUrl('openai', 'dark'),
    name: 'OpenAI GPT',
    description: 'GPT模型',
    website: 'https://openai.com',
    isPrimary: true,
    models: ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4o']
  },
  'chatgpt': {
    color: getSimpleIconUrl('openai', 'color'),
    light: getSimpleIconUrl('openai', 'light'),
    dark: getSimpleIconUrl('openai', 'dark'),
    name: 'ChatGPT',
    description: '对话AI',
    website: 'https://chat.openai.com',
    isPrimary: true
  },

  // === Anthropic 系列 ===
  'anthropic': {
    color: getSimpleIconUrl('anthropic', 'color'),
    light: getSimpleIconUrl('anthropic', 'light'),
    dark: getSimpleIconUrl('anthropic', 'dark'),
    name: 'Anthropic',
    description: 'AI安全',
    website: 'https://anthropic.com',
    isPrimary: true,
    models: ['claude-3', 'claude-2', 'claude-instant'],
    aliases: ['claude']
  },
  'claude': {
    color: getSimpleIconUrl('anthropic', 'color'),
    light: getSimpleIconUrl('anthropic', 'light'),
    dark: getSimpleIconUrl('anthropic', 'dark'),
    name: 'Claude',
    description: 'AI助手',
    website: 'https://claude.ai',
    isPrimary: true,
    models: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku']
  },

  // === Google 系列 ===
  'google': {
    color: getSimpleIconUrl('google', 'color'),
    light: getSimpleIconUrl('google', 'light'),
    dark: getSimpleIconUrl('google', 'dark'),
    name: 'Google',
    description: '谷歌',
    website: 'https://google.com',
    isPrimary: true,
    aliases: ['gemini', 'bard']
  },
  'gemini': {
    color: getSimpleIconUrl('googlegemini', 'color'),
    light: getSimpleIconUrl('googlegemini', 'light'),
    dark: getSimpleIconUrl('googlegemini', 'dark'),
    name: 'Google Gemini',
    description: '多模态AI',
    website: 'https://gemini.google.com',
    isPrimary: true,
    models: ['gemini-pro', 'gemini-ultra', 'gemini-nano']
  },
  'bard': {
    color: getSimpleIconUrl('google', 'color'),
    light: getSimpleIconUrl('google', 'light'),
    dark: getSimpleIconUrl('google', 'dark'),
    name: 'Google Bard',
    description: '对话AI',
    website: 'https://bard.google.com',
    isPrimary: false
  },

  // === Meta 系列 ===
  'meta': {
    color: getSimpleIconUrl('meta', 'color'),
    light: getSimpleIconUrl('meta', 'light'),
    dark: getSimpleIconUrl('meta', 'dark'),
    name: 'Meta',
    description: 'Meta',
    website: 'https://meta.com',
    isPrimary: true,
    aliases: ['llama', 'facebook']
  },
  'llama': {
    color: getSimpleIconUrl('meta', 'color'),
    light: getSimpleIconUrl('meta', 'light'),
    dark: getSimpleIconUrl('meta', 'dark'),
    name: 'Meta LLaMA',
    description: '语言模型',
    website: 'https://llama.meta.com',
    isPrimary: true,
    models: ['llama-2', 'llama-3', 'code-llama']
  },

  // === Microsoft 系列 ===
  'microsoft': {
    color: getSimpleIconUrl('microsoftazure', 'color'), // 使用 Azure 图标代表 Microsoft
    light: getSimpleIconUrl('microsoftazure', 'light'),
    dark: getSimpleIconUrl('microsoftazure', 'dark'),
    name: 'Microsoft',
    description: '微软',
    website: 'https://microsoft.com',
    isPrimary: true,
    aliases: ['copilot', 'bing']
  },
  'copilot': {
    color: getSimpleIconUrl('microsoftcopilot', 'color'),
    light: getSimpleIconUrl('microsoftcopilot', 'light'),
    dark: getSimpleIconUrl('microsoftcopilot', 'dark'),
    name: 'Microsoft Copilot',
    description: 'AI助手',
    website: 'https://copilot.microsoft.com',
    isPrimary: true
  },
  'githubcopilot': {
    color: getSimpleIconUrl('githubcopilot', 'color'),
    light: getSimpleIconUrl('githubcopilot', 'light'),
    dark: getSimpleIconUrl('githubcopilot', 'dark'),
    name: 'GitHub Copilot',
    description: '编程助手',
    website: 'https://github.com/features/copilot',
    isPrimary: true
  },
  'bing': {
    color: getSimpleIconUrl('microsoftbing', 'color'),
    light: getSimpleIconUrl('microsoftbing', 'light'),
    dark: getSimpleIconUrl('microsoftbing', 'dark'),
    name: 'Bing Chat',
    description: 'AI搜索',
    website: 'https://bing.com/chat',
    isPrimary: false
  },

  // === 国产AI模型 ===
  'qwen': {
    color: getSimpleIconUrl('alibabacloud', 'color'), // 使用阿里云图标
    light: getSimpleIconUrl('alibabacloud', 'light'),
    dark: getSimpleIconUrl('alibabacloud', 'dark'),
    name: '通义千问',
    description: '阿里AI',
    website: 'https://tongyi.aliyun.com',
    isPrimary: true,
    models: ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    aliases: ['tongyi', 'alibaba']
  },
  'kimi': {
    color: generatePlaceholderIcon('K'),
    light: generatePlaceholderIcon('K', 'light'),
    dark: generatePlaceholderIcon('K', 'dark'),
    name: 'Kimi',
    description: '智能助手',
    website: 'https://kimi.moonshot.cn',
    isPrimary: true,
    aliases: ['moonshot']
  },
  'moonshot': {
    color: generatePlaceholderIcon('M'),
    light: generatePlaceholderIcon('M', 'light'),
    dark: generatePlaceholderIcon('M', 'dark'),
    name: 'Moonshot AI',
    description: 'AI科技',
    website: 'https://moonshot.cn',
    isPrimary: true,
    aliases: ['kimi']
  },
  'deepseek': {
    color: generatePlaceholderIcon('D'),
    light: generatePlaceholderIcon('D', 'light'),
    dark: generatePlaceholderIcon('D', 'dark'),
    name: 'DeepSeek',
    description: 'AI模型',
    website: 'https://deepseek.com',
    isPrimary: true,
    models: ['deepseek-chat', 'deepseek-coder']
  },
  'bytedance': {
    color: getSimpleIconUrl('bytedance', 'color'),
    light: getSimpleIconUrl('bytedance', 'light'),
    dark: getSimpleIconUrl('bytedance', 'dark'),
    name: '字节跳动',
    description: '字节跳动',
    website: 'https://bytedance.com',
    isPrimary: true,
    aliases: ['doubao', '豆包']
  },
  'doubao': {
    color: getSimpleIconUrl('bytedance', 'color'),
    light: getSimpleIconUrl('bytedance', 'light'),
    dark: getSimpleIconUrl('bytedance', 'dark'),
    name: '豆包',
    description: 'AI助手',
    website: 'https://doubao.com',
    isPrimary: true
  },

  // === 开源和自托管 ===
  'ollama': {
    color: getSimpleIconUrl('ollama', 'color'),
    light: getSimpleIconUrl('ollama', 'light'),
    dark: getSimpleIconUrl('ollama', 'dark'),
    name: 'Ollama',
    description: '本地模型',
    website: 'https://ollama.ai',
    isPrimary: true,
    models: ['llama2', 'mistral', 'codellama']
  },
  'openrouter': {
    color: generatePlaceholderIcon('O'),
    light: generatePlaceholderIcon('O', 'light'),
    dark: generatePlaceholderIcon('O', 'dark'),
    name: 'OpenRouter',
    description: '模型路由',
    website: 'https://openrouter.ai',
    isPrimary: true
  },

  // === 硬件厂商 ===
  'nvidia': {
    color: getSimpleIconUrl('nvidia', 'color'),
    light: getSimpleIconUrl('nvidia', 'light'),
    dark: getSimpleIconUrl('nvidia', 'dark'),
    name: 'NVIDIA',
    description: 'NVIDIA',
    website: 'https://nvidia.com',
    isPrimary: true,
    aliases: ['nim']
  },

  // === 开发工具和框架 ===
  'langchain': {
    color: getSimpleIconUrl('langchain', 'color'),
    light: getSimpleIconUrl('langchain', 'light'),
    dark: getSimpleIconUrl('langchain', 'dark'),
    name: 'LangChain',
    description: '开发框架',
    website: 'https://langchain.com',
    isPrimary: false
  },
  'langgraph': {
    color: generatePlaceholderIcon('L'),
    light: generatePlaceholderIcon('L', 'light'),
    dark: generatePlaceholderIcon('L', 'dark'),
    name: 'LangGraph',
    description: '工作流',
    website: 'https://langchain.com/langgraph',
    isPrimary: false
  },

  // === 其他工具 ===
  'cursor': {
    color: getSimpleIconUrl('cursor', 'color'),
    light: getSimpleIconUrl('cursor', 'light'),
    dark: getSimpleIconUrl('cursor', 'dark'),
    name: 'Cursor',
    description: '代码编辑',
    website: 'https://cursor.sh',
    isPrimary: false
  },
  'cline': {
    color: generatePlaceholderIcon('C'),
    light: generatePlaceholderIcon('C', 'light'),
    dark: generatePlaceholderIcon('C', 'dark'),
    name: 'Cline',
    description: '编程助手',
    website: 'https://github.com/cline/cline',
    isPrimary: false
  },
  'github': {
    color: getSimpleIconUrl('github', 'color'),
    light: getSimpleIconUrl('github', 'light'),
    dark: getSimpleIconUrl('github', 'dark'),
    name: 'GitHub',
    description: '代码托管',
    website: 'https://github.com',
    isPrimary: false
  },
  'aws': {
    color: getSimpleIconUrl('amazonaws', 'color'),
    light: getSimpleIconUrl('amazonaws', 'light'),
    dark: getSimpleIconUrl('amazonaws', 'dark'),
    name: 'Amazon Web Services',
    description: 'AWS',
    website: 'https://aws.amazon.com',
    isPrimary: false,
    aliases: ['amazon']
  },
  'grok': {
    color: getSimpleIconUrl('x', 'color'),
    light: getSimpleIconUrl('x', 'light'),
    dark: getSimpleIconUrl('x', 'dark'),
    name: 'Grok',
    description: 'AI助手',
    website: 'https://x.ai',
    isPrimary: true,
    aliases: ['xai', 'x.ai']
  },

  // === 其他AI模型 ===
  'mistral': {
    color: getSimpleIconUrl('mistralai', 'color'),
    light: getSimpleIconUrl('mistralai', 'light'),
    dark: getSimpleIconUrl('mistralai', 'dark'),
    name: 'Mistral AI',
    description: 'AI研究',
    website: 'https://mistral.ai',
    isPrimary: true,
    models: ['mistral-7b', 'mixtral-8x7b']
  },
  'mixtral': {
    color: getSimpleIconUrl('mistralai', 'color'),
    light: getSimpleIconUrl('mistralai', 'light'),
    dark: getSimpleIconUrl('mistralai', 'dark'),
    name: 'Mixtral',
    description: '专家模型',
    website: 'https://mistral.ai',
    isPrimary: true
  },
  'perplexity': {
    color: getSimpleIconUrl('perplexity', 'color'),
    light: getSimpleIconUrl('perplexity', 'light'),
    dark: getSimpleIconUrl('perplexity', 'dark'),
    name: 'Perplexity AI',
    description: 'AI搜索',
    website: 'https://perplexity.ai',
    isPrimary: true
  },
  'huggingface': {
    color: getSimpleIconUrl('huggingface', 'color'),
    light: getSimpleIconUrl('huggingface', 'light'),
    dark: getSimpleIconUrl('huggingface', 'dark'),
    name: 'Hugging Face',
    description: '模型托管',
    website: 'https://huggingface.co',
    isPrimary: true
  },
  'baidu': {
    color: getSimpleIconUrl('baidu', 'color'),
    light: getSimpleIconUrl('baidu', 'light'),
    dark: getSimpleIconUrl('baidu', 'dark'),
    name: '百度',
    description: '百度',
    website: 'https://baidu.com',
    isPrimary: true,
    aliases: ['wenxin', '文心']
  },

  // === 金融市场相关 ===
  'bitcoin': {
    color: getSimpleIconUrl('bitcoin', 'color'),
    light: getSimpleIconUrl('bitcoin', 'light'),
    dark: getSimpleIconUrl('bitcoin', 'dark'),
    name: 'Bitcoin',
    description: '比特币',
    website: 'https://bitcoin.org',
    isPrimary: false
  },
  'ethereum': {
    color: getSimpleIconUrl('ethereum', 'color'),
    light: getSimpleIconUrl('ethereum', 'light'),
    dark: getSimpleIconUrl('ethereum', 'dark'),
    name: 'Ethereum',
    description: '以太坊',
    website: 'https://ethereum.org',
    isPrimary: false
  },
  'binance': {
    color: getSimpleIconUrl('binance', 'color'),
    light: getSimpleIconUrl('binance', 'light'),
    dark: getSimpleIconUrl('binance', 'dark'),
    name: 'Binance',
    description: '币安',
    website: 'https://binance.com',
    isPrimary: false
  },
  'cryptocurrency': {
    color: generatePlaceholderIcon('C'),
    light: generatePlaceholderIcon('C', 'light'),
    dark: generatePlaceholderIcon('C', 'dark'),
    name: 'Cryptocurrency',
    description: '加密货币',
    isPrimary: false
  },
  
  // === 科技公司 ===
  'apple': {
    color: getSimpleIconUrl('apple', 'color'),
    light: getSimpleIconUrl('apple', 'light'),
    dark: getSimpleIconUrl('apple', 'dark'),
    name: 'Apple',
    description: '苹果公司',
    website: 'https://apple.com',
    isPrimary: false
  },
  'tesla': {
    color: getSimpleIconUrl('tesla', 'color'),
    light: getSimpleIconUrl('tesla', 'light'),
    dark: getSimpleIconUrl('tesla', 'dark'),
    name: 'Tesla',
    description: '特斯拉',
    website: 'https://tesla.com',
    isPrimary: false
  },
  'amazon': {
    color: getSimpleIconUrl('amazon', 'color'),
    light: getSimpleIconUrl('amazon', 'light'),
    dark: getSimpleIconUrl('amazon', 'dark'),
    name: 'Amazon',
    description: '亚马逊',
    website: 'https://amazon.com',
    isPrimary: false
  },
  
  // === 分析工具相关 ===
  'tradingview': {
    color: getSimpleIconUrl('tradingview', 'color'),
    light: getSimpleIconUrl('tradingview', 'light'),
    dark: getSimpleIconUrl('tradingview', 'dark'),
    name: 'TradingView',
    description: '技术分析',
    website: 'https://tradingview.com',
    isPrimary: false
  },
  'uniswap': {
    color: generatePlaceholderIcon('U'),
    light: generatePlaceholderIcon('U', 'light'),
    dark: generatePlaceholderIcon('U', 'dark'),
    name: 'Uniswap',
    description: 'DeFi协议',
    website: 'https://uniswap.org',
    isPrimary: false
  },
  'twitter': {
    color: getSimpleIconUrl('x', 'color'),
    light: getSimpleIconUrl('x', 'light'),
    dark: getSimpleIconUrl('x', 'dark'),
    name: 'Twitter',
    description: '社交媒体',
    website: 'https://twitter.com',
    isPrimary: false,
    aliases: ['x']
  },
  'yahoo': {
    color: getSimpleIconUrl('yahoo', 'color'),
    light: getSimpleIconUrl('yahoo', 'light'),
    dark: getSimpleIconUrl('yahoo', 'dark'),
    name: 'Yahoo Finance',
    description: '财经资讯',
    website: 'https://finance.yahoo.com',
    isPrimary: false
  },

  // === 默认图标 ===
  'default': {
    color: generatePlaceholderIcon('?'),
    light: generatePlaceholderIcon('?', 'light'),
    dark: generatePlaceholderIcon('?', 'dark'),
    name: 'Unknown Provider',
    description: '未知'
  }
}

/**
 * 获取Logo配置
 * @param provider - 提供商标识
 * @returns Logo配置对象
 */
export function getLogoConfig(provider: string): LogoConfig {
  if (!provider) return logoProviderMap.default
  
  const normalizedProvider = provider.toLowerCase().trim()
  
  // 直接匹配
  if (logoProviderMap[normalizedProvider]) {
    return logoProviderMap[normalizedProvider]
  }
  
  // 别名匹配
  for (const [key, config] of Object.entries(logoProviderMap)) {
    if (config.aliases?.some(alias => alias.toLowerCase() === normalizedProvider)) {
      return config
    }
  }
  
  // 部分匹配
  for (const [key, config] of Object.entries(logoProviderMap)) {
    if (normalizedProvider.includes(key) || key.includes(normalizedProvider)) {
      return config
    }
  }
  
  return logoProviderMap.default
}

/**
 * 获取Logo URL
 * @param provider - 提供商标识
 * @param theme - 主题（'light' | 'dark' | 'color'）
 * @returns Logo URL
 */
export function getLogoUrl(provider: string, theme: 'light' | 'dark' | 'color' = 'color'): string {
  const config = getLogoConfig(provider)
  
  // 优先使用彩色版本
  if (theme === 'color' && config.color) {
    return config.color
  }
  
  // 使用对应主题的版本
  if (theme === 'dark' && config.dark) {
    return config.dark
  }
  
  if (theme === 'light' && config.light) {
    return config.light
  }
  
  // 回退到任何可用的版本
  return config.color || config.light || config.dark || config.fallback || generatePlaceholderIcon(provider)
}

/**
 * Logo解析选项
 */
export interface LogoResolveOptions {
  /** 主题 */
  theme?: 'light' | 'dark'
  /** 是否优先使用彩色版本 */
  preferColor?: boolean
  /** 是否启用回退 */
  enableFallback?: boolean
}

/**
 * 解析Logo路径
 * @param provider - 提供商标识
 * @param options - 解析选项
 * @returns 包含路径和配置的对象
 */
export function resolveLogoPath(
  provider: string,
  options: LogoResolveOptions = {}
): { path: string; config: LogoConfig } {
  const { theme = 'light', preferColor = false, enableFallback = true } = options
  const config = getLogoConfig(provider)
  
  let path: string
  
  // 如果优先使用彩色版本且存在彩色图标
  if (preferColor && config.color) {
    path = config.color
  } else if (theme === 'dark' && config.dark) {
    // 使用深色主题图标
    path = config.dark
  } else if (theme === 'light' && config.light) {
    // 使用浅色主题图标
    path = config.light
  } else if (config.color) {
    // 回退到彩色版本
    path = config.color
  } else if (config.light) {
    // 回退到浅色版本
    path = config.light
  } else if (config.dark) {
    // 回退到深色版本
    path = config.dark
  } else if (config.fallback) {
    // 使用指定的回退图标
    path = config.fallback
  } else if (enableFallback) {
    // 生成占位符
    path = generatePlaceholderIcon(config.name || provider)
  } else {
    // 没有可用的图标
    path = ''
  }
  
  return { path, config }
}