import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { AnalysisConfig, AnalysisResult, AnalysisHistory, AgentStatus, AnalysisStep } from '../types/analysis'
import * as analysisApi from '../api/analysis'
import { normalizeTokenUsage as sharedNormalizeTokenUsage } from '@/utils/tokenNormalizer'
import { createI18n } from 'vue-i18n'

// 为工具名称创建独立的i18n实例
const toolI18n = createI18n({
  locale: 'zh-CN',
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': {
      tools: {
        names: {
          finnhub_news: 'FinnHub新闻',
          reddit_sentiment: 'Reddit情绪分析',
          sentiment_batch: '批量情绪分析',
          crypto_price: '加密货币价格',
          indicators: '技术指标',
          market_data: '市场数据',
          historical_data: '历史数据',
          market_metrics: '市场指标',
          trending: '热门币种',
          fear_greed: '恐惧贪婪指数',
          batch_execution: '批量执行'
        }
      }
    },
    'en-US': {
      tools: {
        names: {
          finnhub_news: 'FinnHub News',
          reddit_sentiment: 'Reddit Sentiment',
          sentiment_batch: 'Batch Sentiment',
          crypto_price: 'Crypto Price',
          indicators: 'Technical Indicators',
          market_data: 'Market Data',
          historical_data: 'Historical Data',
          market_metrics: 'Market Metrics',
          trending: 'Trending Coins',
          fear_greed: 'Fear & Greed Index',
          batch_execution: 'Batch Execution'
        }
      }
    }
  }
})

// 获取工具名称翻译的函数
const getToolTranslation = (toolId: string): string => {
  try {
    const locale = localStorage.getItem('when-trade-locale') || 'zh-CN'
    toolI18n.global.locale = locale as 'zh-CN' | 'en-US'
    const t = toolI18n.global.t
    const translationKey = `tools.names.${toolId}`
    const result = t(translationKey) as string
    
    // 如果翻译结果与key相同，说明没有找到翻译，返回原始toolId
    if (result === translationKey) {
      return toolId
    }
    
    return result
  } catch (error) {
    console.warn(`获取工具翻译失败: ${toolId}`, error)
    return toolId
  }
}

// 保存活跃的WebSocket取消订阅函数
let activeUnsubscribers: Array<() => void> = []
let activeAnalysisId: string | null = null



export const useAnalysisStore = defineStore('analysis', () => {
  
  // Current analysis state
  const currentAnalysis = ref<AnalysisResult | null>(null)
  const currentResult = ref<AnalysisResult | null>(null)
  const isAnalyzing = ref(false)
  const analysisProgress = ref(0)
  const currentStep = ref<AnalysisStep | null>(null)
  
  // Analysis history
  const analysisHistory = ref<AnalysisHistory[]>([])
  
  // Agent status - 初始为空，根据市场类型动态加载
  const agents = ref<AgentStatus[]>([])
  
  // Error state
  const error = ref<string | null>(null)
  
  // Agent thoughts for real-time updates
  const agentThoughts = ref<Array<{
    agent: string
    thought: string
    timestamp: string
    phase?: string
    phaseOrder?: number
    nodeOrder?: number
    isPhaseComplete?: boolean
    phaseName?: string
  }>>([])
  
  // Agent status updates for real-time status changes
  const agentStatusUpdates = ref<Array<{
    agent: string
    status: 'idle' | 'processing' | 'completed' | 'error'
    phase?: string
    timestamp: string
  }>>([])
  
  // 分析开始时间，用于准确计算分析时长
  const analysisStartTime = ref<number | null>(null)
  
  // Computed properties
  const activeAgents = computed(() => 
    agents.value.filter((agent: any) => agent.status !== 'idle')
  )
  
  const averageConfidence = computed(() => {
    const activeAgentsList = activeAgents.value
    if (activeAgentsList.length === 0) return 0
    return activeAgentsList.reduce((sum: number, agent: any) => sum + agent.confidence, 0) / activeAgentsList.length
  })
  
  const isComplete = computed(() => 
    analysisProgress.value >= 100 && agents.value.every((agent: any) => 
      agent.status === 'completed' || agent.status === 'idle'
    )
  )

  // 更新可用的 agents
  const updateAvailableAgents = (marketAgents: any[]) => {
    agents.value = marketAgents.map(agent => ({
      id: agent.id,
      name: agent.name,
      avatar: getAgentAvatar(agent.type || agent.id),
      role: agent.type || agent.id,
      type: agent.type || agent.id,
      status: 'idle',
      progress: 0,
      currentTask: 'Idle',
      lastUpdate: 'Just now',
      thoughts: [],
      confidence: 0
    }))
  }
  
  // 清空 agents
  const clearAgents = () => {
    agents.value = []
  }

  // 开始流程分析
  const startFlowAnalysis = async (flowConfig: any) => {
    // 将流程配置转换为标准配置
    const formData = {
      marketType: flowConfig.marketType || 'crypto',
      symbol: flowConfig.symbol || 'BTC/USDT',
      timeframe: flowConfig.timeframe || '1h',
      depth: flowConfig.depth || 3,
      analysisScopes: [],
      llmProvider: flowConfig.llmProvider || 'openai',
      llmModel: flowConfig.llmModel || 'gpt-4-turbo-preview',
      flowConfig // 保存流程配置
    }
    
    // 从流程节点中提取分析范围
    flowConfig.nodes.forEach((node: any) => {
      if (node.type === 'agent' && node.config?.agentType) {
        formData.analysisScopes.push(node.config.agentType)
      }
    })
    
    // 开始标准分析流程
    await startAnalysis(formData)
  }
  
  // WebSocket连接和监听函数
  const connectWebSocketForAnalysis = async (analysisId: string, config: AnalysisConfig) => {
    // console.log('🔌 准备连接WebSocket监听分析进度...')
    try {
      // 从 websocket service 获取连接状态
      const { websocketService } = await import('@/services/websocket')
      
      if (!websocketService.isConnected) {
        // console.log('📡 WebSocket未连接，正在建立连接...')
        // 简化版本使用无认证连接
        await websocketService.connect()
      }
      
      // console.log('✅ WebSocket已连接，开始监听分析进度')
      
      // 订阅分析相关消息
      const unsubscribeProgress = websocketService.subscribe('task.progress', (message: any) => {
        if (message.data.taskId === analysisId || message.data.analysisId === analysisId) {
          analysisProgress.value = message.data.progress || 0
          // 更新当前步骤
          if (message.data.currentStep) {
            currentStep.value = {
              id: 'current',
              name: message.data.currentStep,
              description: message.data.message || '',
              progress: message.data.progress || 0,
              status: 'running'
            }
          }
        }
      })
      
      // 订阅Agent思考消息（包含完整phase信息）
      const unsubscribeThought = websocketService.subscribe('agent.thought', (message: any) => {
        // console.log('🤖 收到Agent思考:', message.data)
        if (message.data.analysisId === analysisId) {
          agentThoughts.value.push({
            agent: message.data.agent,
            thought: message.data.thought,
            timestamp: message.data.timestamp || new Date().toISOString(),
            // 添加阶段相关信息
            phase: message.data.phase,
            phaseOrder: message.data.phaseOrder,
            nodeOrder: message.data.nodeOrder,
            isPhaseComplete: message.data.isPhaseComplete,
            phaseName: message.data.phaseName
          })
        }
      })
      
      // Linus原则：订阅工具调用消息
      const unsubscribeTool = websocketService.subscribe('agent.tool', (message: any) => {
        // console.log('🔧 收到工具调用:', message.data)
        if (message.data.analysisId === analysisId) {
          // 处理工具名称本地化
          let toolDisplayText = message.data.tool
          if (message.data.tool) {
            // 处理多个工具（逗号分隔）
            if (message.data.tool.includes(',')) {
              const tools = message.data.tool.split(',').map((t: string) => t.trim())
              const translatedTools = tools.map((t: string) => getToolTranslation(t))
              toolDisplayText = translatedTools.join(', ')
            } else {
              toolDisplayText = getToolTranslation(message.data.tool)
            }
          }
          
          // 将工具调用消息加入思考流，以便UI显示
          agentThoughts.value.push({
            agent: message.data.agent,
            thought: message.data.message || `调用工具: ${toolDisplayText}`,
            timestamp: message.data.timestamp || new Date().toISOString(),
            phase: message.data.phase,
            phaseOrder: message.data.phaseOrder,
            nodeOrder: message.data.nodeOrder,
            isPhaseComplete: false,
            phaseName: message.data.phaseName,
            isTool: true,  // 标记为工具调用
            tool: message.data.tool,
            args: message.data.args
          })
        }
      })
      
      // 订阅Agent状态消息
      const unsubscribeStatus = websocketService.subscribe('agent.status', (message: any) => {
        // console.log('🔄 收到Agent状态更新:', message.data)
        if (message.data.analysisId === analysisId || message.data.taskId === analysisId) {
          agentStatusUpdates.value.push({
            agent: message.data.agent,
            status: message.data.status,
            phase: message.data.phase,
            timestamp: message.data.timestamp || new Date().toISOString()
          })
        }
      })
      
      const unsubscribeComplete = websocketService.subscribe('analysis.complete', async (message: any) => {
        // console.log('🎉 分析完成:', message.data.analysisId)
        
        if (message.data.analysisId === analysisId) {
          isAnalyzing.value = false
          analysisProgress.value = 100
          
          // 应用统一的数据规范化处理
          const finalResult = normalizeAnalysisData(message.data.result, config)
          
          currentAnalysis.value = finalResult
          currentResult.value = finalResult
          
          if (finalResult.token_usage) {
            if (finalResult.token_usage._estimated) {
            } else {
              // console.log('💰 [成本] 使用真实的 token_usage:', finalResult.token_usage)
            }
          } else {
            if (import.meta.env.DEV) {
              console.debug('⚠️ [成本] 规范化后仍未找到 token 使用量数据')
            }
          }
          
          // 保存到历史记录 - 使用规范化的数据
          const historyEntry: AnalysisHistory = {
            id: Date.now().toString(),
            config: {
              ...config,
              marketType: config.market_type || config.marketType || config.parameters?.market_type || 'crypto',
              symbol: config.symbol,
              timeframe: config.timeframe,
              depth: config.depth,
              analysisScopes: config.parameters?.analysis_scopes || config.analysis_scopes || config.analysisScopes || [],
              // 使用规范化的 provider（moonshot -> kimi），确保始终有值
              llmProvider: finalResult._normalized_provider || 
                          config.parameters?.llm_provider || 
                          config.llm_provider || 
                          config.llmProvider || 
                          'unknown',
              llmModel: config.parameters?.llm_model || config.llm_model || config.llmModel,
              analysts: config.parameters?.analysis_scopes || config.analysis_scopes || config.analysisScopes || config.analysts || [],
              language: localStorage.getItem('when-trade-locale') || 'zh-CN'
            },
            result: finalResult, // 直接使用规范化后的完整结果
            timestamp: Date.now(),
            duration: analysisStartTime.value ? Date.now() - analysisStartTime.value : 0,
            cost: message.data.cost || (() => {
              const duration = analysisStartTime.value ? Date.now() - analysisStartTime.value : 1000
              const baseRate = 0.001
              const depthMultiplier = config.depth || 1
              const scopeMultiplier = (config.analysisScopes?.length || config.analysis_scopes?.length || 1) * 0.5
              return Math.min((duration / 1000) * baseRate * depthMultiplier * scopeMultiplier, 0.1)
            })(),
            steps: [],
            agentThoughts: agentThoughts.value // 保存完整的Agent思考数据
          }
          
          // 立即生成并保存完整报告和简洁报告
          try {
            const { generateReportFromHistory, generateMarkdownReport, generateSimpleMarkdownReport } = await import('@/utils/reportGenerator')
            const reportData = generateReportFromHistory(historyEntry)
            historyEntry.report = generateMarkdownReport(reportData)
            historyEntry.simpleReport = generateSimpleMarkdownReport(historyEntry)
            // console.log('📄 已生成完整分析报告和简洁报告')
          } catch (reportError) {
            if (import.meta.env.DEV) {
              console.debug('⚠️ 生成报告失败:', reportError)
            }
          }
          
          analysisHistory.value.unshift(historyEntry)
          saveToLocalStorage()
          // console.log('💾 分析结果已保存到历史记录')
          
          // 清理订阅
          unsubscribeProgress()
          unsubscribeComplete()
          unsubscribeThought()
          unsubscribeTool()
        }
      })
      
      const unsubscribeError = websocketService.subscribe('error', (message: any) => {
        console.error('❌ 分析出错:', message.data)
        error.value = message.data.message || '分析失败'
        isAnalyzing.value = false
        
        // 清理订阅
        unsubscribeProgress()
        unsubscribeComplete()
        unsubscribeError()
        unsubscribeThought()
        unsubscribeTool()
      })
      
      // 保存所有取消订阅函数到全局数组
      activeUnsubscribers = [
        unsubscribeProgress,
        unsubscribeThought,
        unsubscribeTool,
        unsubscribeStatus,
        unsubscribeComplete,
        unsubscribeError
      ]
      activeAnalysisId = analysisId
      
      // WebSocket只订阅已存在任务的更新，不创建新任务
      // 任务已经通过REST API创建，这里只需要监听更新
      // console.log(`📡 WebSocket已连接，监听任务 ${analysisId} 的更新`)
      
      // 订阅分析任务的更新（传递完整参数，符合Linus原则：消除特殊情况）
      // 处理两种参数格式：原始AnalysisConfig 和 转换后的API参数
      
      // Phase 2.5: 从config对象读取用户选择的工具配置
      // 根据实际的config结构，工具配置在顶层的selected_tools和selected_data_sources字段
      const allSelectedTools: string[] = config.selected_tools || config.tools || (config.parameters?.selected_tools) || []
      const allSelectedDataSources: string[] = config.selected_data_sources || config.dataSources || (config.parameters?.selected_data_sources) || []
      
      // console.log(`🔧 [Phase 2.5] 从config读取工具配置: ${allSelectedTools.length} 个工具，${allSelectedDataSources.length} 个数据源`)
      // console.log('🔧 [Phase 2.5] 收集到的工具:', allSelectedTools)
      // console.log('🔧 [Phase 2.5] 收集到的数据源:', allSelectedDataSources)
      
      // 【调试】记录分析范围
      const analysisScopes = config.analysis_scopes || config.analysisScopes || (config.parameters?.analysis_scopes) || []
      
      // 获取当前语言设置
      const currentLanguage = localStorage.getItem('when-trade-locale') || 'zh-CN'
      
      const normalizedParams = {
        symbol: config.symbol,
        analysis_type: config.analysis_type || 'comprehensive',
        timeframe: config.timeframe || '1h',
        language: currentLanguage,  // 添加语言参数
        parameters: {
          market_type: config.market_type || config.marketType || (config.parameters?.market_type) || 'crypto',
          depth: Number(config.depth) || Number(config.parameters?.depth) || 3,
          analysis_scopes: analysisScopes,
          selected_tools: allSelectedTools,
          selected_data_sources: allSelectedDataSources,
          llm_provider: config.llm_provider || config.llmProvider || (config.parameters?.llm_provider),
          llm_model: config.llm_model || config.llmModel || (config.parameters?.llm_model),
          language: currentLanguage  // 在parameters中也添加语言参数以防后端从这里读取
        }
      }
      
      // console.log('🔧 WebSocket订阅参数:', normalizedParams)
      // console.log('🔍 DEBUG: config对象内容:', JSON.stringify(config, null, 2))
      // console.log('🔍 DEBUG: 分析范围来源检查:', {
      //   'config.analysis_scopes': config.analysis_scopes,
      //   'config.analysisScopes': config.analysisScopes, 
      //   'config.parameters?.analysis_scopes': config.parameters?.analysis_scopes,
      //   'normalizedParams.parameters.analysis_scopes': normalizedParams.parameters.analysis_scopes
      // })
      websocketService.subscribeToAnalysis(analysisId, normalizedParams)
      
    } catch (wsError: any) {
      console.error('❌ WebSocket连接失败:', wsError)
      console.warn('⚠️ WebSocket失败，降级到轮询模式')
      
      // 降级到轮询API状态
      await pollAnalysisStatus(analysisId, config)
    }
  }
  
  // 轮询分析状态（WebSocket失败时的降级方案）
  const pollAnalysisStatus = async (analysisId: string, config?: AnalysisConfig) => {
    const maxPolls = 60 // 最多轮询5分钟（每5秒一次）
    let pollCount = 0
    
    const pollInterval = setInterval(async () => {
      try {
        pollCount++
        const status = await analysisApi.getAnalysisStatus(analysisId)
        // console.log(`📋 轮询状态 (${pollCount}/${maxPolls}):`, status)
        
        analysisProgress.value = status.progress || 0
        
        if (status.current_step) {
          currentStep.value = status.current_step
        }
        
        if (status.status === 'completed') {
          // console.log('✅ 轮询检测到分析完成')
          isAnalyzing.value = false
          analysisProgress.value = 100
          
          // 获取最终结果
          try {
            const result = await analysisApi.getAnalysisResult(analysisId)
            currentAnalysis.value = result
            currentResult.value = result
            
            // 保存到历史记录（如果提供了config）
            if (config) {
              const historyEntry: AnalysisHistory = {
                id: Date.now().toString(),
                config: {
                  ...config,
                  marketType: config.market_type || config.marketType || config.parameters?.market_type || 'crypto',
                  symbol: config.symbol,
                  timeframe: config.timeframe,
                  depth: config.depth,
                  analysisScopes: config.parameters?.analysis_scopes || config.analysis_scopes || config.analysisScopes || [],
                  llmProvider: config.llm_provider || config.llmProvider || 'unknown',
                  llmModel: config.llm_model || config.llmModel,
                  analysts: config.parameters?.analysis_scopes || config.analysis_scopes || config.analysisScopes || config.analysts || [],
                  language: localStorage.getItem('when-trade-locale') || 'zh-CN'
                },
                result: result,
                timestamp: Date.now(),
                duration: analysisStartTime.value ? Date.now() - analysisStartTime.value : 0,
                cost: (() => {
                  const duration = analysisStartTime.value ? Date.now() - analysisStartTime.value : 1000
                  const baseRate = 0.001
                  const depthMultiplier = config.depth || 1
                  const scopeMultiplier = (config.analysisScopes?.length || config.analysis_scopes?.length || 1) * 0.5
                  return Math.min((duration / 1000) * baseRate * depthMultiplier * scopeMultiplier, 0.1)
                })(),
                steps: [],
                agentThoughts: agentThoughts.value // 保存完整的Agent思考数据
              }
              
              // 立即生成并保存完整报告和简洁报告
              try {
                const { generateReportFromHistory, generateMarkdownReport, generateSimpleMarkdownReport } = await import('@/utils/reportGenerator')
                const reportData = generateReportFromHistory(historyEntry)
                historyEntry.report = generateMarkdownReport(reportData)
                historyEntry.simpleReport = generateSimpleMarkdownReport(historyEntry)
                // console.log('📄 轮询模式：已生成完整分析报告和简洁报告')
              } catch (reportError) {
                if (import.meta.env.DEV) {
                  console.debug('⚠️ 轮询模式：生成报告失败:', reportError)
                }
              }
              
              analysisHistory.value.unshift(historyEntry)
              saveToLocalStorage()
              // console.log('💾 轮询模式：已保存分析历史记录')
            }
          } catch (resultError) {
            if (import.meta.env.DEV) {
              console.debug('⚠️ 获取分析结果失败:', resultError)
            }
          }
          
          clearInterval(pollInterval)
        } else if (status.status === 'failed') {
          console.error('❌ 轮询检测到分析失败')
          error.value = status.error || '分析失败'
          isAnalyzing.value = false
          clearInterval(pollInterval)
        } else if (pollCount >= maxPolls) {
          console.warn('⏰ 轮询超时')
          error.value = '分析超时'
          isAnalyzing.value = false
          clearInterval(pollInterval)
        }
      } catch (pollError) {
        console.error('❌ 轮询出错:', pollError)
        pollCount++
        if (pollCount >= maxPolls) {
          error.value = '无法获取分析状态'
          isAnalyzing.value = false
          clearInterval(pollInterval)
        }
      }
    }, 5000) // 每5秒轮询一次
  }
  
  // 获取 agent 头像
  const getAgentAvatar = (type: string): string => {
    const avatarMap: Record<string, string> = {
      'technical_analyst': '📊',
      'technicalanalyst': '📊',
      'fundamental_analyst': '📈',
      'fundamentalanalyst': '📈',
      'sentiment_analyst': '😊',
      'sentimentanalyst': '😊',
      'risk_analyst': '⚠️',
      'riskanalyst': '⚠️',
      'market_analyst': '🌍',
      'marketanalyst': '🌍',
      'crypto_trend_analyst': '🪙',
      'cryptotrendanalyst': '🪙',
      'odds_analyst': '🎯',
      'oddsanalyst': '🎯',
      'liquidity_analyst': '💧',
      'liquidityanalyst': '💧',
      'event_impact_analyst': '📰',
      'eventimpactanalyst': '📰',
      'bullish_researcher': '🐂',
      'bearish_researcher': '🐻',
      'optimistic_analyst': '🌟',
      'pessimistic_analyst': '🌧️'
    }
    return avatarMap[type.toLowerCase()] || '🤖'
  }



  // Actions
  const startAnalysis = async (config: AnalysisConfig) => {
    try {
      // 清理之前的WebSocket订阅
      if (activeUnsubscribers.length > 0) {
        // console.log('🧹 清理之前的WebSocket订阅...')
        activeUnsubscribers.forEach(unsubscribe => {
          try {
            unsubscribe()
          } catch (error) {
            console.warn('清理订阅失败:', error)
          }
        })
        activeUnsubscribers = []
      }
      
      isAnalyzing.value = true
      error.value = null
      analysisProgress.value = 0
      
      // 记录分析开始时间
      analysisStartTime.value = Date.now()
      
      // 清空所有历史数据，确保每次分析从干净状态开始
      agentThoughts.value = []        // 清空Agent思考
      agentStatusUpdates.value = []   // 清空Agent状态更新
      currentAnalysis.value = null    // 清空当前分析
      currentResult.value = null      // 清空当前结果
      currentStep.value = null        // 清空当前步骤
      
      // Reset agent status
      agents.value.forEach(agent => {
        agent.status = 'idle'
        agent.progress = 0
        agent.thoughts = []
        agent.confidence = 0
        agent.currentTask = ''
      })

      // 只使用真实API数据

      // 尝试调用后端API
      let analysis_id: string
      try {
        // console.log('🚀 尝试调用后端API创建分析任务...')
        
        // 【DEBUG】详细检查 analysis_scopes 的来源
        // console.log('🔍 [DEBUG] analysis_scopes 来源检查:')
        // console.log('  - config.parameters?.analysis_scopes:', config.parameters?.analysis_scopes)
        // console.log('  - config.analysis_scopes:', config.analysis_scopes)
        // console.log('  - config.analysisScopes:', config.analysisScopes)
        
        const finalAnalysisScopes = config.parameters?.analysis_scopes || config.analysis_scopes || config.analysisScopes || []
        // console.log('🎯 [DEBUG] 最终使用的 analysis_scopes:', finalAnalysisScopes)
        
        // Phase 2: 调试工具配置
        // console.log('🔧 [Phase 2] 检查工具配置:')
        // console.log('  - config.selected_tools:', config.selected_tools)
        // console.log('  - config.selected_data_sources:', config.selected_data_sources)
        
        const apiRequest = {
          market_type: config.market_type || config.marketType || 'crypto',
          symbol: config.symbol,
          timeframe: config.timeframe,
          depth: String(config.parameters?.depth || config.depth || 3),  // 优先使用parameters.depth，兼容直接传递的depth
          analysis_scopes: finalAnalysisScopes,
          llm_provider: config.parameters?.llm_provider || config.llm_provider || config.llmProvider,
          llm_model: config.parameters?.llm_model || config.llm_model || config.llmModel,
          // Phase 2: 添加工具配置
          selected_tools: config.selected_tools || [],
          selected_data_sources: config.selected_data_sources || []
        }
        // console.log('📝 API请求参数:', apiRequest)
        // console.log('🔧 [Phase 2] 最终工具数量:', apiRequest.selected_tools.length)
        
        const response = await analysisApi.startAnalysis(apiRequest)
        analysis_id = response.analysis_id
        // console.log('✅ API调用成功，analysis_id:', analysis_id)
        
        // 连接WebSocket监听实时更新
        await connectWebSocketForAnalysis(analysis_id, config)
        return
        
      } catch (apiError: any) {
        console.error('❌ API调用失败，详细错误信息:', {
          error: apiError,
          message: apiError?.message,
          status: apiError?.status,
          response: apiError?.response?.data,
          stack: apiError?.stack
        })
        
        // 诊断当前认证状态
        // 根据错误类型提供不同的诊断建议
        if (apiError?.status === 422) {
          console.error('📝 请求验证失败 - 检查请求参数')
          console.error('   建议：检查请求参数格式和必填字段')
          error.value = '请求参数无效'
        } else if (apiError?.status === 404) {
          console.error('🔍 API端点不存在')
          console.error('   建议：检查后端服务是否正常运行')
          error.value = 'API端点不存在'
        } else if (apiError?.code === 'NETWORK_ERROR') {
          console.error('🌐 网络连接错误')
          console.error('   建议：检查网络连接状态')
          error.value = '网络连接失败'
        } else {
          error.value = `API调用失败: ${apiError?.message || '未知错误'}`
        }
        
        // API失败，抛出错误
        console.error('❌ API调用失败，无法继续分析')
        throw new Error(error.value)
      }
      
      // 轮询获取分析状态
      // 不再使用本地步骤，依赖API返回的状态
      
      // 记录开始时间用于计算真实时长
      const startTime = Date.now()
      
      // 轮询检查分析状态
      let analysisComplete = false
      
      while (!analysisComplete && isAnalyzing.value) {
        // Check if stopped by user
        if (!isAnalyzing.value) {
          // Analysis stopped by user, exiting loop
          break
        }
        
        // 获取最新状态
        const status = await analysisApi.getAnalysisStatus(analysis_id)
        
        // 更新进度
        analysisProgress.value = status.progress || 0
        currentStep.value = status.current_step || null
        
        // 更新智能体状态
        if (status.agents) {
          status.agents.forEach(agentData => {
            const agent = agents.value.find(a => a.id === agentData.id)
            if (agent) {
              agent.status = agentData.status
              agent.progress = agentData.progress
              agent.thoughts = agentData.thoughts
              agent.confidence = agentData.confidence
              agent.currentTask = agentData.current_task
            }
          })
        }
        
        // 检查是否完成
        if (status.status === 'completed') {
          analysisComplete = true
        } else if (status.status === 'failed') {
          throw new Error(status.error || 'Analysis failed')
        }
        
        // 等待一段时间再轮询
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // 再次检查是否被用户停止
        if (!isAnalyzing.value) {
          // 分析在智能体工作后被停止，退出循环
          break
        }
        
        // 等待一段时间再轮询
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      
      // 获取最终分析结果
      const result = await analysisApi.getAnalysisResult(analysis_id)
      currentAnalysis.value = result
      currentResult.value = result
      
      // 提取token使用量数据
      const tokenUsage = result?.agents_insights?.token_usage || result?.token_usage || null
      if (tokenUsage) {
        // console.log('💰 [成本-轮询] 提取到 token_usage:', tokenUsage)
      }
      
      // 计算真实的分析时长
      const actualDuration = Date.now() - startTime
      
      // 从结果中提取真实成本，如果没有则计算估算成本
      let actualCost = 0
      if (result.agents_insights && typeof result.agents_insights === 'object') {
        // 尝试从agents_insights中提取cost
        actualCost = result.agents_insights.cost || result.agents_insights.total_cost || 0
      }
      
      // 如果没有真实成本数据，基于分析时长和深度进行估算
      if (actualCost === 0) {
        const baseRate = 0.001 // 每秒基础费用
        const depthMultiplier = config.depth || 1
        const scopeMultiplier = (config.analysisScopes?.length || 1) * 0.5
        actualCost = (actualDuration / 1000) * baseRate * depthMultiplier * scopeMultiplier
        actualCost = Math.min(actualCost, 0.1) // 设置最大成本上限
      }
      
      // 添加到历史记录
      const historyEntry: AnalysisHistory = {
        id: Date.now().toString(),
        config: {
          ...config,
          // 确保使用驼峰格式
          marketType: config.market_type || config.marketType || 'unknown',
          symbol: config.symbol,
          timeframe: config.timeframe,
          depth: config.depth,
          analysisScopes: config.analysis_scopes || config.analysisScopes || [],
          // 与WebSocket分支保持一致，优先从parameters读取
          llmProvider: config.parameters?.llm_provider || config.llm_provider || config.llmProvider || 'unknown',
          llmModel: config.parameters?.llm_model || config.llm_model || config.llmModel,
          analysts: config.analysts || config.analysisScopes || [],
          language: localStorage.getItem('when-trade-locale') || 'zh-CN'
        },
        result: {
          ...result,
          // 确保token_usage在result顶层可以被找到
          token_usage: tokenUsage || result?.token_usage
        },
        timestamp: Date.now(),
        duration: actualDuration, // 使用真实的分析时长
        cost: actualCost, // 使用真实或估算的成本
        steps: steps.map(s => ({ ...s, status: 'completed', progress: 100 })),
        agentThoughts: agentThoughts.value // 保存完整的Agent思考数据
      }
      
      // 立即生成并保存完整报告和简洁报告
      try {
        const { generateReportFromHistory, generateMarkdownReport, generateSimpleMarkdownReport } = await import('@/utils/reportGenerator')
        const reportData = generateReportFromHistory(historyEntry)
        historyEntry.report = generateMarkdownReport(reportData)
        historyEntry.simpleReport = generateSimpleMarkdownReport(historyEntry)
        // console.log('📄 startAnalysis：已生成完整分析报告和简洁报告')
      } catch (reportError) {
        if (import.meta.env.DEV) {
          console.debug('⚠️ startAnalysis：生成报告失败:', reportError)
        }
      }
      
      analysisHistory.value.unshift(historyEntry)
      saveToLocalStorage()
      
      // 分析完成后保持状态显示
      agents.value.forEach(agent => {
        agent.status = 'completed'
        agent.progress = 100
        agent.currentTask = 'Analysis completed'
      })
      
      // 保持分析完成状态 - 关键修复
      isAnalyzing.value = false
      analysisProgress.value = 100
      // 保持currentStep显示最后一步，确保UI能正确显示完成状态
      currentStep.value = { ...steps[steps.length - 1], status: 'completed', progress: 100 }
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred during analysis'
      isAnalyzing.value = false
      currentStep.value = null
      
      // 错误时重置智能体状态
      agents.value.forEach(agent => {
        agent.status = 'idle'
        agent.progress = 0
        agent.currentTask = ''
      })
    }
  }
  
  // 添加停止分析的方法
  const stopAnalysis = async () => {
    if (!isAnalyzing.value) return
    
    // console.log('🛑 停止分析...')
    
    // 1. 通过WebSocket发送取消消息（关键修复！）
    if (activeAnalysisId) {
      // console.log(`📡 发送WebSocket取消消息: ${activeAnalysisId}`)
      try {
        const { websocketService } = await import('@/services/websocket')
        if (websocketService.isConnected) {
          websocketService.cancelAnalysis(activeAnalysisId)
          // console.log('✅ WebSocket取消消息已发送')
        } else {
          console.warn('⚠️ WebSocket未连接，无法发送取消消息')
        }
      } catch (error) {
        console.warn('发送WebSocket取消消息失败:', error)
      }
    }
    
    // 2. 取消所有WebSocket订阅
    if (activeUnsubscribers.length > 0) {
      // console.log('📡 取消WebSocket订阅...')
      activeUnsubscribers.forEach(unsubscribe => {
        try {
          unsubscribe()
        } catch (error) {
          console.warn('取消订阅失败:', error)
        }
      })
      activeUnsubscribers = []
    }
    
    // 3. 清理任务ID和更新前端状态
    if (activeAnalysisId) {
      // console.log(`🔌 清理任务ID: ${activeAnalysisId}`)
      activeAnalysisId = null
    }
    
    // 4. 更新前端状态
    isAnalyzing.value = false
    error.value = 'Analysis stopped by user'
    
    // 保持当前进度，不重置
    agents.value.forEach(agent => {
      if (agent.status === 'thinking' || agent.status === 'analyzing') {
        agent.status = 'idle'
        agent.currentTask = 'Analysis stopped'
      }
    })
    
    // console.log('✅ 分析已停止')
  }

  // 添加重置分析状态的方法
  const resetAnalysis = () => {
    isAnalyzing.value = false
    analysisProgress.value = 0
    currentStep.value = null
    currentAnalysis.value = null
    currentResult.value = null
    error.value = null
    
    agents.value.forEach(agent => {
      agent.status = 'idle'
      agent.progress = 0
      agent.currentTask = ''
      agent.thoughts = []
      agent.confidence = 0
    })
  }

  // 统一数据规范化函数 - 消除字段名和数据结构的差异
  const normalizeAnalysisData = (rawData: any, config: any) => {
    // 1. 规范化 provider ID
    const normalizeProvider = (p: string | undefined): string => {
      if (!p) return 'unknown'  // 明确返回 'unknown' 而不是空字符串
      
      const normalized = p.toLowerCase().trim()
      
      // 统一别名映射
      const aliasMap: Record<string, string> = {
        'moonshot': 'kimi',
        'moonshot.ai': 'kimi',
        'claude': 'anthropic',
        'gpt': 'openai',
        'chatgpt': 'openai',
        'gpt-3.5': 'openai',
        'gpt-4': 'openai'
      }
      
      return aliasMap[normalized] || normalized
    }
    
    // 2. 规范化 token 使用量 - 统一字段名和数据位置
    const normalizeTokenUsage = (data: any, config: any) => {
      // 从多个可能位置查找 token 数据
      const usage = data?.agents_insights?.token_usage || 
                    data?.token_usage || 
                    data?.usage || 
                    data?.token_count || 
                    null
      
      if (usage) {
        // 使用共享的规范化函数
        const normalized = sharedNormalizeTokenUsage(usage)
        if (normalized.totalTokens > 0) {
          return {
            input_tokens: normalized.inputTokens,
            output_tokens: normalized.outputTokens,
            total_tokens: normalized.totalTokens
          }
        }
      }
      
      // 兜底：基于文本内容估算（仅对适合的数据）
      const estimated = estimateTokenUsage(data, config)
      if (estimated) {
        return estimated
      }
      
      // 完全没有可用数据，静默返回
      return null
    }
    
    // Token 估算函数 - 当后端没有提供真实数据时使用
    const estimateTokenUsage = (data: any, config: any) => {
      // 早期检查：排除结构化对象
      if (typeof data === 'object' && data !== null) {
        // 检查是否为业务结果对象
        const businessKeys = ['company', 'date', 'signal', 'analysis', 'type']
        if (businessKeys.some(key => key in data)) {
          // 静默跳过业务结果对象
          return null
        }
        
        // 检查是否为工具调用或其他非文本对象
        if ('tool_call' in data || 'choices' in data) {
          // 静默跳过工具调用等结构
          return null
        }
      }
      
      // 智能提取文本内容 - 适配多种数据结构
      const extractText = (obj: any): string => {
        if (typeof obj === 'string') return obj
        if (obj?.content) return obj.content
        if (obj?.text) return obj.text
        if (obj?.message) return obj.message
        if (Array.isArray(obj)) return obj.map(extractText).join(' ')
        if (typeof obj === 'object' && obj !== null) {
          // 从对象中提取所有字符串值
          return Object.values(obj)
            .filter(v => typeof v === 'string' && v.length > 10)
            .join(' ')
        }
        return ''
      }
      
      // 从实际分析结果中提取文本
      const textFields = [
        'market_report', 'social_report', 'news_report',
        'fundamentals_report', 'bull_case', 'bear_case', 
        'trade_decision', 'company', 'signal'
      ]
      
      const totalText = textFields
        .map(field => extractText(data?.[field]))
        .filter(Boolean)
        .join(' ')
      
      // 最小长度检查：只对足够长的文本估算
      if (!totalText || totalText.length < 20) {
        // 静默返回，不打印警告
        return null
      }
      
      // 基于文本长度估算 - 考虑中英文混合
      const charCount = totalText.length
      const estimatedOutputTokens = Math.round(charCount / 3) // 保守估算
      
      // 输入token估算（分析配置、数据请求等）
      const baseInputTokens = 500 // 基础请求token
      const depthMultiplier = (config?.depth || 1) * 200 // 深度影响
      const scopeMultiplier = (config?.analysisScopes?.length || config?.parameters?.analysis_scopes?.length || 1) * 100
      const estimatedInputTokens = baseInputTokens + depthMultiplier + scopeMultiplier
      
      
      return {
        input_tokens: estimatedInputTokens,
        output_tokens: estimatedOutputTokens,
        total_tokens: estimatedInputTokens + estimatedOutputTokens,
        _estimated: true // 标记为估算值
      }
    }
    
    const normalizedTokenUsage = normalizeTokenUsage(rawData, config)
    const normalizedProvider = normalizeProvider(
      config?.parameters?.llm_provider || 
      config?.llm_provider || 
      config?.llmProvider
    )
    
    // 只在开发环境下记录调试信息
    if (import.meta.env.DEV && !normalizedTokenUsage) {
      console.debug('⚠️ [规范化] 未找到 token 使用量数据, 原始结构:', Object.keys(rawData || {}))
    }
    if (import.meta.env.DEV && normalizedProvider !== (config?.llm_provider || config?.llmProvider)) {
      console.debug('📊 [规范化] Provider 归一化:', config?.llm_provider, '->', normalizedProvider)
    }
    
    return {
      ...rawData,
      // 确保 token_usage 在顶层且格式统一
      token_usage: normalizedTokenUsage,
      // 保存规范化的 provider 用于历史记录
      _normalized_provider: normalizedProvider
    }
  }

  const getRelevantAgents = (stepId: string): string[] => {
    // 动态根据当前 agents 返回相关的 agent ids
    const agentIds = agents.value.map(a => a.id)
    
    const stepAgentMap: Record<string, (ids: string[]) => string[]> = {
      '1': () => [], // 数据收集不需要特定智能体
      '2': (ids) => ids.filter(id => id.includes('technical')),
      '3': (ids) => ids.filter(id => id.includes('fundamental')), 
      '4': (ids) => ids.filter(id => id.includes('sentiment')),
      '5': (ids) => ids.filter(id => id.includes('risk')),
      '6': (ids) => ids, // 所有 agents 参与辩论
      '7': (ids) => ids  // 所有 agents 参与最终报告
    }
    
    const mapFn = stepAgentMap[stepId]
    return mapFn ? mapFn(agentIds) : []
  }



  const clearHistory = () => {
    analysisHistory.value = []
    // 清除所有相关的localStorage keys
    localStorage.removeItem('analysis_history')
    localStorage.removeItem('analysis_history_default-user')
    // console.log('🧹 已清理所有历史记录数据')
  }

  const deleteHistoryItem = (id: string) => {
    const index = analysisHistory.value.findIndex(item => item.id === id)
    if (index > -1) {
      analysisHistory.value.splice(index, 1)
      saveToLocalStorage()
    }
  }

  const saveToLocalStorage = () => {
    try {
      // 添加用户ID前缀，确保数据隔离
      const userId = 'default-user'
      if (!userId) return
      
      const key = `analysis_history_${userId}`
      localStorage.setItem(key, JSON.stringify(analysisHistory.value))
    } catch (err) {
      // 无法保存分析历史到本地存储
    }
  }

  const loadFromLocalStorage = () => {
    try {
      // 使用用户ID前缀加载数据
      const userId = 'default-user'
      if (!userId) {
        // 未登录时清空历史
        analysisHistory.value = []
        return
      }
      
      const key = `analysis_history_${userId}`
      const saved = localStorage.getItem(key)
      
      if (saved) {
        const parsed = JSON.parse(saved)
        // 验证数据格式，过滤掉无效的记录
        analysisHistory.value = parsed.filter((item: any) => 
          item && item.config && item.config.symbol && item.timestamp
        )
        // 从localStorage加载有效记录
      } else {
        // 尝试迁移旧数据（一次性）
        const oldData = localStorage.getItem('analysis_history')
        if (oldData) {
          try {
            const parsed = JSON.parse(oldData)
            analysisHistory.value = parsed.filter((item: any) => 
              item && item.config && item.config.symbol && item.timestamp
            )
            saveToLocalStorage() // 保存到新的key
            localStorage.removeItem('analysis_history') // 删除旧数据
      } catch {
            // 旧数据损坏，清理
            localStorage.removeItem('analysis_history')
      }
      }
      }
    } catch (err) {
      // 无法从本地存储加载分析历史
      // 清理损坏的数据
      const userId = 'default-user'
      if (userId) {
        localStorage.removeItem(`analysis_history_${userId}`)
      }
      analysisHistory.value = []
    }
  }

  // 历史数据迁移：补充缺失的 provider 信息
  const migrateHistoryProviders = () => {
    let migrated = false
    analysisHistory.value = analysisHistory.value.map(h => {
      if (!h.config?.llmProvider && !h.config?.llm_provider) {
        // 尝试从其他字段推断
        const provider = h.config?.parameters?.llm_provider || 
                        h.result?._normalized_provider || 
                        'legacy'
        
        // 确保 config 对象存在
        if (!h.config) h.config = {}
        h.config.llmProvider = provider
        migrated = true
        console.info('🔄 [迁移] 为历史记录补充 provider:', { 
          symbol: h.config.symbol, 
          provider,
          timestamp: h.timestamp 
        })
      }
      return h
    })
    
    if (migrated) {
      saveToLocalStorage()
      console.info('✅ [迁移] 历史数据迁移完成，已保存到本地存储')
    }
  }

  // 简化版本无需监听登录状态

  // 初始化时加载历史记录
  loadFromLocalStorage()
  // 执行数据迁移
  migrateHistoryProviders()
  
  // 只使用真实的分析历史记录

  // 动态分析相关方法
  const createAnalysis = async (params: {
    symbol: string
    marketType: string
    domains: string[]
    scenario?: string
    enableDynamic?: boolean
  }) => {
    try {
      // 调用后端API创建分析任务
      const analysisRequest = {
        symbol: params.symbol,
        market_type: params.marketType,
        analysis_depth: params.domains.length, // 根据选择的领域数量设置深度
        analysts: params.domains, // 使用选择的领域作为分析师列表
        llm_config: {
          provider: 'deepseek',
          model: 'deepseek-chat',
          temperature: 0.7
        }
      }

      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }

      // 简化版本无需认证头

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/analysis/tasks`, {
        method: 'POST',
        headers,
        body: JSON.stringify(analysisRequest)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '创建分析任务失败')
      }

      const task = await response.json()
      
      // 创建agents列表（基于传入的domains）
      const agentMap: Record<string, { name: string, color: string }> = {
        'technical_analysis': { name: '技术分析师', color: '#3B82F6' },
        'fundamental_analysis': { name: '基本面分析师', color: '#8B5CF6' },
        'sentiment_analysis': { name: '情绪分析师', color: '#EC4899' },
        'risk_analysis': { name: '风险分析师', color: '#EF4444' },
        'market_analysis': { name: '市场分析师', color: '#10B981' },
        'crypto_trend_analysis': { name: '加密趋势分析师', color: '#F59E0B' },
      }

      const agents = params.domains.map(domain => {
        const agentInfo = agentMap[domain] || { name: domain, color: '#6B7280' }
        return {
          id: domain,
          name: agentInfo.name,
          domain: domain,
          status: 'idle',
          color: agentInfo.color
      }
      })

      const stages = [
        { id: 'data_collection', name: '数据收集', status: 'pending', agentCount: 1 },
        { id: 'analysis', name: '深度分析', status: 'pending', agentCount: agents.length },
        { id: 'synthesis', name: '综合总结', status: 'pending', agentCount: 1 }
      ]

      return {
        analysisId: task.id,
        agents,
        stages,
        task
      }

    } catch (error: any) {
      console.error('创建分析任务失败:', error)
      throw error
    }
  }

  // 获取分析任务详情
  const getAnalysisTask = async (taskId: string) => {
    try {
      const headers: Record<string, string> = {}
      // 简化版本无需认证头

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/analysis/tasks/${taskId}`, {
        method: 'GET',
        headers
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '获取分析任务失败')
      }

      return await response.json()
    } catch (error: any) {
      console.error('获取分析任务失败:', error)
      throw error
    }
  }

  // 取消分析任务
  const cancelAnalysisTask = async (taskId: string) => {
    try {
      const headers: Record<string, string> = {}
      // 简化版本无需认证头

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/analysis/tasks/${taskId}/cancel`, {
        method: 'POST',
        headers
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '取消分析任务失败')
      }

      return await response.json()
    } catch (error: any) {
      console.error('取消分析任务失败:', error)
      throw error
    }
  }

  // 获取用户的分析任务列表
  const getUserAnalysisTasks = async (status?: string, limit: number = 50, offset: number = 0) => {
    try {
      const headers: Record<string, string> = {}
      // 简化版本无需认证头

      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString()
      })

      if (status) {
        params.append('status', status)
      }

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/analysis/tasks?${params}`, {
        method: 'GET',
        headers
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || '获取分析任务列表失败')
      }

      return await response.json()
    } catch (error: any) {
      console.error('获取分析任务列表失败:', error)
      throw error
    }
  }

  return {
    // State
    currentAnalysis,
    currentResult,
    isAnalyzing,
    analysisProgress,
    currentStep,
    analysisHistory,
    agents,
    error,
    agentThoughts,
    agentStatusUpdates,
    analysisStartTime,
    
    // Computed
    activeAgents,
    averageConfidence,
    isComplete,
    
    // Actions
    startAnalysis,
    startFlowAnalysis,
    stopAnalysis,
    resetAnalysis,
    clearHistory,
    deleteHistoryItem,
    loadFromLocalStorage,
    createAnalysis,
    getAnalysisTask,
    cancelAnalysisTask,
    getUserAnalysisTasks,
    updateAvailableAgents,
    clearAgents,
    
    // 更新历史记录的报告内容
    updateHistoryReport: (historyId: string, report: string) => {
      const historyIndex = analysisHistory.value.findIndex(h => h.id === historyId)
      if (historyIndex !== -1) {
        analysisHistory.value[historyIndex].report = report
        saveToLocalStorage()
        // console.log('💾 已更新历史记录报告内容:', historyId)
      }
    }
  }
})