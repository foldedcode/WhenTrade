import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

// 实际使用的Agent类型
type AgentType = 
  | 'market' | 'technical' | 'onchain' | 'sentiment' | 'defi' | 'fundamental'
  | 'bull' | 'bear' | 'manager' | 'trader' | 'risky' | 'safe' | 'neutral' 
  | 'judge' | 'portfolio' | 'event' | 'probability' | 'odds'
  | 'social' | 'news' | 'fundamentals'

// 提示词模板接口
interface PromptTemplate {
  role: string
  dataSection: string
  analysisPoints: string[]
  analysisInstruction: string
  outputRequirements: string[]
  outputInstruction: string
}

// Agent类型到模板键的映射
const AGENT_TYPE_TO_TEMPLATE_KEY: Record<string, string> = {
  'market': 'technical',
  'technical': 'technical',
  'onchain': 'onchain', 
  'sentiment': 'sentiment',
  'social': 'sentiment',
  'defi': 'defi',
  'fundamental': 'fundamental',
  'fundamentals': 'fundamental',
  'news': 'sentiment',
  'bull': 'bullish',
  'bear': 'bearish',
  'manager': 'manager',
  'trader': 'trader',
  'risky': 'aggressive',
  'safe': 'conservative',
  'neutral': 'neutral',
  'judge': 'neutral', // 风险评判员使用中性模板
  'portfolio': 'portfolio',
  'event': 'event',
  'probability': 'probability',
  'odds': 'odds'
}

/**
 * 多语言提示词服务
 * 根据当前语言环境动态生成agent分析提示词
 */
export class MultilingualPromptsService {
  private i18n: ReturnType<typeof useI18n>
  private promptTemplates = ref<Record<string, PromptTemplate>>({})
  
  constructor() {
    this.i18n = useI18n()
    this.loadPromptTemplates()
  }

  /**
   * 加载当前语言的提示词模板
   */
  private async loadPromptTemplates() {
    try {
      const locale = this.i18n.locale.value
      let templates: Record<string, PromptTemplate>
      
      // 动态导入对应语言的提示词模板
      if (locale === 'zh-CN') {
        const module = await import('@/locales/zh-CN/agent-prompts.json')
        templates = module.default.templates
      } else if (locale === 'en-US') {
        const module = await import('@/locales/en-US/agent-prompts.json')
        templates = module.default.templates
      } else {
        // 默认使用英文模板
        const module = await import('@/locales/en-US/agent-prompts.json')
        templates = module.default.templates
      }
      
      this.promptTemplates.value = templates
    } catch (error) {
      console.error('Failed to load prompt templates:', error)
      // 使用默认模板作为降级方案
      this.promptTemplates.value = {
        default: {
          role: 'You are {agentName}, analyzing {symbol}.',
          dataSection: 'Data:',
          analysisPoints: [],
          analysisInstruction: '',
          outputRequirements: ['Please provide professional analysis (50-80 words).'],
          outputInstruction: ''
        }
      }
    }
  }

  /**
   * 监听语言变化并重新加载模板
   */
  public watchLocaleChange() {
    // 监听语言变化
    this.i18n.locale.value && this.loadPromptTemplates()
  }

  /**
   * 获取指定agent类型的提示词模板
   */
  public getPromptTemplate(agentType: AgentType): PromptTemplate {
    const templateKey = AGENT_TYPE_TO_TEMPLATE_KEY[agentType] || 'default'
    return this.promptTemplates.value[templateKey] || this.promptTemplates.value.default
  }

  /**
   * 构建完整的分析提示词
   */
  public buildAnalysisPrompt(
    agentType: AgentType,
    agentName: string,
    symbol: string,
    data: string,
    analysisDepth: string = 'standard'
  ): string {
    const template = this.getPromptTemplate(agentType)
    
    // 替换模板变量
    const role = template.role
      .replace('{agentName}', agentName)
      .replace('{symbol}', symbol)
    
    // 构建分析要点
    let analysisPoints = ''
    if (template.analysisPoints.length > 0) {
      analysisPoints = template.analysisPoints
        .map((point, index) => `${index + 1}. ${point}`)
        .join('\n')
    }
    
    // 构建输出要求
    const outputRequirements = template.outputRequirements
      .map((req, index) => `${index + 1}. ${req}`)
      .join('\n')
    
    // 组装完整提示词
    const promptParts = [
      role,
      '',
      template.dataSection,
      data,
      ''
    ]
    
    if (template.analysisInstruction && analysisPoints) {
      promptParts.push(
        template.analysisInstruction,
        analysisPoints,
        ''
      )
    }
    
    if (template.outputInstruction) {
      promptParts.push(
        template.outputInstruction,
        outputRequirements
      )
    } else {
      promptParts.push(outputRequirements)
    }
    
    return promptParts.join('\n')
  }

  /**
   * 获取agent显示名称（多语言）
   */
  public getAgentDisplayName(agentType: AgentType): string {
    return this.i18n.t(`agents.names.${agentType}`) || agentType
  }

  /**
   * 检查模板是否已加载
   */
  public get isTemplatesLoaded(): boolean {
    return Object.keys(this.promptTemplates.value).length > 0
  }

  /**
   * 获取当前语言环境
   */
  public get currentLocale(): string {
    return this.i18n.locale.value
  }
}

// 创建单例实例
let multilingualPromptsService: MultilingualPromptsService | null = null

/**
 * 获取多语言提示词服务实例
 */
export function useMultilingualPrompts(): MultilingualPromptsService {
  if (!multilingualPromptsService) {
    multilingualPromptsService = new MultilingualPromptsService()
  }
  return multilingualPromptsService
}

/**
 * 重置服务实例（用于语言切换时）
 */
export function resetMultilingualPrompts(): void {
  multilingualPromptsService = null
}