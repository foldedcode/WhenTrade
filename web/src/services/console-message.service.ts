/**
 * 前端控制台输出多语言消息管理
 * 
 * 统一管理所有前端控制台输出、错误信息和调试日志的多语言内容。
 * 消除硬编码中文字符串，支持动态语言切换。
 */

import { ref } from 'vue'
import { localeService } from './locale.service'
import type { AvailableLocales } from '../locales'

interface ConsoleMessage {
  time: string
  type: 'system' | 'agent' | 'tool' | 'error'
  content: string
  agent?: string
}

// 前端控制台消息定义
const CONSOLE_MESSAGES = {
  'en': {
    // 系统和初始化
    system: {
      startup: 'System starting up...',
      initialization: 'Initialization complete',
      configuration_loaded: 'Configuration loaded',
      service_started: 'Service started',
      service_stopped: 'Service stopped'
    },
    
    // WebSocket相关
    websocket: {
      connecting: 'Connecting to WebSocket...',
      connected: 'WebSocket connected successfully',
      disconnected: 'WebSocket disconnected',
      reconnecting: 'Reconnecting to WebSocket...',
      connection_failed: 'WebSocket connection failed',
      message_sent: 'Message sent to WebSocket',
      message_received: 'Message received from WebSocket',
      subscription_started: 'Started subscription to analysis updates',
      subscription_failed: 'Failed to subscribe to analysis updates',
      heartbeat_sent: 'Heartbeat sent',
      heartbeat_failed: 'Heartbeat failed',
      auth_required: 'Authentication required for WebSocket connection',
      auth_success: 'WebSocket authentication successful',
      auth_failed: 'WebSocket authentication failed'
    },
    
    // 分析相关
    analysis: {
      started: 'Analysis started',
      completed: 'Analysis completed',
      failed: 'Analysis failed',
      cancelled: 'Analysis cancelled',
      progress_updated: 'Analysis progress updated',
      scope_selected: 'Analysis scope selected',
      agents_initialized: 'Analysis agents initialized',
      report_generated: 'Analysis report generated',
      data_loading: 'Loading analysis data...',
      data_loaded: 'Analysis data loaded',
      data_error: 'Error loading analysis data',
      stream_started: 'Analysis stream started',
      stream_ended: 'Analysis stream ended',
      chunk_received: 'Analysis chunk received',
      phase_changed: 'Analysis phase changed',
      agent_status_updated: 'Agent status updated'
    },
    
    // LLM相关
    llm: {
      detection_started: 'Starting LLM provider detection...',
      detection_completed: 'LLM provider detection completed',
      detection_failed: 'LLM provider detection failed, using default configuration',
      providers_found: 'Available LLM providers found',
      no_providers: 'No LLM providers available',
      model_list_loading: 'Loading model list...',
      model_list_loaded: 'Model list loaded successfully',
      model_list_failed: 'Failed to load model list',
      config_updated: 'LLM configuration updated',
      config_invalid: 'Invalid LLM configuration',
      api_key_missing: 'API key missing for LLM provider',
      api_key_invalid: 'Invalid API key for LLM provider',
      request_started: 'LLM request started',
      request_completed: 'LLM request completed',
      request_failed: 'LLM request failed',
      stream_started: 'LLM stream started',
      stream_chunk: 'LLM stream chunk received',
      stream_ended: 'LLM stream ended',
      stream_error: 'LLM stream error',
      cost_calculated: 'LLM usage cost calculated',
      usage_tracked: 'LLM usage tracked'
    },
    
    // 成本控制
    cost: {
      tracking_enabled: 'Cost tracking enabled',
      tracking_disabled: 'Cost tracking disabled',
      budget_set: 'Budget limit set',
      budget_exceeded: 'Budget limit exceeded',
      budget_warning: 'Budget warning threshold reached',
      usage_calculated: 'Usage cost calculated',
      usage_recorded: 'Usage recorded',
      report_generated: 'Cost report generated',
      optimization_suggested: 'Cost optimization suggestions available'
    },
    
    // 性能监控
    performance: {
      monitoring_started: 'Performance monitoring started',
      monitoring_stopped: 'Performance monitoring stopped',
      metrics_collected: 'Performance metrics collected',
      slow_operation: 'Slow operation detected',
      memory_usage_high: 'High memory usage detected',
      cpu_usage_high: 'High CPU usage detected',
      network_slow: 'Slow network detected',
      optimization_applied: 'Performance optimization applied',
      benchmark_completed: 'Performance benchmark completed'
    },
    
    // 数据处理
    data: {
      loading: 'Loading data...',
      loaded: 'Data loaded successfully',
      loading_failed: 'Data loading failed',
      processing: 'Processing data...',
      processed: 'Data processed successfully',
      processing_failed: 'Data processing failed',
      caching: 'Caching data...',
      cached: 'Data cached successfully',
      cache_hit: 'Data cache hit',
      cache_miss: 'Data cache miss',
      validation_started: 'Data validation started',
      validation_passed: 'Data validation passed',
      validation_failed: 'Data validation failed',
      transformation_started: 'Data transformation started',
      transformation_completed: 'Data transformation completed',
      sync_started: 'Data synchronization started',
      sync_completed: 'Data synchronization completed',
      sync_failed: 'Data synchronization failed'
    },
    
    // 用户界面
    ui: {
      component_mounted: 'Component mounted',
      component_unmounted: 'Component unmounted',
      component_updated: 'Component updated',
      component_error: 'Component error',
      route_changed: 'Route changed',
      navigation_started: 'Navigation started',
      navigation_completed: 'Navigation completed',
      navigation_cancelled: 'Navigation cancelled',
      form_submitted: 'Form submitted',
      form_validation_failed: 'Form validation failed',
      modal_opened: 'Modal opened',
      modal_closed: 'Modal closed',
      notification_shown: 'Notification shown',
      notification_dismissed: 'Notification dismissed'
    },
    
    // 国际化
    i18n: {
      language_changed: 'Language changed',
      language_loading: 'Loading language resources...',
      language_loaded: 'Language resources loaded',
      language_failed: 'Failed to load language resources',
      translation_missing: 'Translation missing',
      locale_detected: 'Locale detected',
      locale_fallback: 'Using fallback locale',
      content_loading: 'Loading localized content...',
      content_loaded: 'Localized content loaded',
      content_failed: 'Failed to load localized content',
      check_started: 'i18n completeness check started',
      check_completed: 'i18n completeness check completed',
      missing_keys_found: 'Missing translation keys found',
      unused_keys_found: 'Unused translation keys found',
      report_generated: 'i18n report generated'
    },
    
    // 错误处理
    error: {
      network_error: 'Network error occurred',
      api_error: 'API error occurred',
      validation_error: 'Validation error',
      authentication_error: 'Authentication error',
      authorization_error: 'Authorization error',
      timeout_error: 'Request timeout',
      server_error: 'Server error',
      client_error: 'Client error',
      unknown_error: 'Unknown error occurred',
      error_boundary: 'Error boundary caught error',
      error_reported: 'Error reported to monitoring service',
      error_recovered: 'Recovered from error'
    },
    
    // 通用状态
    status: {
      success: 'Success',
      failed: 'Failed',
      error: 'Error',
      warning: 'Warning',
      info: 'Info',
      debug: 'Debug',
      loading: 'Loading',
      completed: 'Completed',
      cancelled: 'Cancelled',
      timeout: 'Timeout',
      retry: 'Retry',
      skipped: 'Skipped',
      pending: 'Pending',
      processing: 'Processing',
      idle: 'Idle'
    }
  },
  
  'zh-CN': {
    // 系统和初始化
    system: {
      startup: '系统启动中...',
      initialization: '初始化完成',
      configuration_loaded: '配置已加载',
      service_started: '服务已启动',
      service_stopped: '服务已停止'
    },
    
    // WebSocket相关
    websocket: {
      connecting: '正在连接WebSocket...',
      connected: 'WebSocket连接成功',
      disconnected: 'WebSocket连接断开',
      reconnecting: '正在重新连接WebSocket...',
      connection_failed: 'WebSocket连接失败',
      message_sent: '消息已发送到WebSocket',
      message_received: '从WebSocket接收到消息',
      subscription_started: '开始订阅分析更新',
      subscription_failed: '订阅分析更新失败',
      heartbeat_sent: '心跳已发送',
      heartbeat_failed: '心跳发送失败',
      auth_required: 'WebSocket连接需要身份验证',
      auth_success: 'WebSocket身份验证成功',
      auth_failed: 'WebSocket身份验证失败'
    },
    
    // 分析相关
    analysis: {
      started: '分析已开始',
      completed: '分析已完成',
      failed: '分析失败',
      cancelled: '分析已取消',
      progress_updated: '分析进度已更新',
      scope_selected: '分析范围已选择',
      agents_initialized: '分析代理已初始化',
      report_generated: '分析报告已生成',
      data_loading: '正在加载分析数据...',
      data_loaded: '分析数据加载完成',
      data_error: '分析数据加载错误',
      stream_started: '分析流已开始',
      stream_ended: '分析流已结束',
      chunk_received: '接收到分析数据块',
      phase_changed: '分析阶段已变更',
      agent_status_updated: '代理状态已更新'
    },
    
    // LLM相关
    llm: {
      detection_started: '开始检测LLM提供商...',
      detection_completed: 'LLM提供商检测完成',
      detection_failed: 'LLM提供商检测失败，使用默认配置',
      providers_found: '发现可用的LLM提供商',
      no_providers: '没有可用的LLM提供商',
      model_list_loading: '正在加载模型列表...',
      model_list_loaded: '模型列表加载成功',
      model_list_failed: '模型列表加载失败',
      config_updated: 'LLM配置已更新',
      config_invalid: 'LLM配置无效',
      api_key_missing: 'LLM提供商API密钥缺失',
      api_key_invalid: 'LLM提供商API密钥无效',
      request_started: 'LLM请求已开始',
      request_completed: 'LLM请求已完成',
      request_failed: 'LLM请求失败',
      stream_started: 'LLM流已开始',
      stream_chunk: '接收到LLM流数据块',
      stream_ended: 'LLM流已结束',
      stream_error: 'LLM流错误',
      cost_calculated: 'LLM使用成本已计算',
      usage_tracked: 'LLM使用情况已跟踪'
    },
    
    // 成本控制
    cost: {
      tracking_enabled: '成本跟踪已启用',
      tracking_disabled: '成本跟踪已禁用',
      budget_set: '预算限制已设置',
      budget_exceeded: '预算限制已超出',
      budget_warning: '已达到预算警告阈值',
      usage_calculated: '使用成本已计算',
      usage_recorded: '使用情况已记录',
      report_generated: '成本报告已生成',
      optimization_suggested: '成本优化建议可用'
    },
    
    // 性能监控
    performance: {
      monitoring_started: '性能监控已开始',
      monitoring_stopped: '性能监控已停止',
      metrics_collected: '性能指标已收集',
      slow_operation: '检测到慢操作',
      memory_usage_high: '检测到高内存使用',
      cpu_usage_high: '检测到高CPU使用',
      network_slow: '检测到网络缓慢',
      optimization_applied: '性能优化已应用',
      benchmark_completed: '性能基准测试完成'
    },
    
    // 数据处理
    data: {
      loading: '正在加载数据...',
      loaded: '数据加载成功',
      loading_failed: '数据加载失败',
      processing: '正在处理数据...',
      processed: '数据处理成功',
      processing_failed: '数据处理失败',
      caching: '正在缓存数据...',
      cached: '数据缓存成功',
      cache_hit: '数据缓存命中',
      cache_miss: '数据缓存未命中',
      validation_started: '数据验证已开始',
      validation_passed: '数据验证通过',
      validation_failed: '数据验证失败',
      transformation_started: '数据转换已开始',
      transformation_completed: '数据转换已完成',
      sync_started: '数据同步已开始',
      sync_completed: '数据同步已完成',
      sync_failed: '数据同步失败'
    },
    
    // 用户界面
    ui: {
      component_mounted: '组件已挂载',
      component_unmounted: '组件已卸载',
      component_updated: '组件已更新',
      component_error: '组件错误',
      route_changed: '路由已变更',
      navigation_started: '导航已开始',
      navigation_completed: '导航已完成',
      navigation_cancelled: '导航已取消',
      form_submitted: '表单已提交',
      form_validation_failed: '表单验证失败',
      modal_opened: '模态框已打开',
      modal_closed: '模态框已关闭',
      notification_shown: '通知已显示',
      notification_dismissed: '通知已关闭'
    },
    
    // 国际化
    i18n: {
      language_changed: '语言已切换',
      language_loading: '正在加载语言资源...',
      language_loaded: '语言资源加载完成',
      language_failed: '语言资源加载失败',
      translation_missing: '翻译缺失',
      locale_detected: '语言环境已检测',
      locale_fallback: '使用备用语言环境',
      content_loading: '正在加载本地化内容...',
      content_loaded: '本地化内容加载完成',
      content_failed: '本地化内容加载失败',
      check_started: 'i18n完整性检查已开始',
      check_completed: 'i18n完整性检查已完成',
      missing_keys_found: '发现缺失的翻译键',
      unused_keys_found: '发现未使用的翻译键',
      report_generated: 'i18n报告已生成'
    },
    
    // 错误处理
    error: {
      network_error: '网络错误',
      api_error: 'API错误',
      validation_error: '验证错误',
      authentication_error: '身份验证错误',
      authorization_error: '授权错误',
      timeout_error: '请求超时',
      server_error: '服务器错误',
      client_error: '客户端错误',
      unknown_error: '未知错误',
      error_boundary: '错误边界捕获错误',
      error_reported: '错误已报告给监控服务',
      error_recovered: '已从错误中恢复'
    },
    
    // 通用状态
    status: {
      success: '成功',
      failed: '失败',
      error: '错误',
      warning: '警告',
      info: '信息',
      debug: '调试',
      loading: '加载中',
      completed: '已完成',
      cancelled: '已取消',
      timeout: '超时',
      retry: '重试',
      skipped: '已跳过',
      pending: '等待中',
      processing: '处理中',
      idle: '空闲'
    }
  }
} as const

/**
 * 控制台消息服务 - 支持多语言的控制台输出管理
 * 单例模式确保全局唯一实例
 */
class ConsoleMessageService {
  private static instance: ConsoleMessageService | null = null
  
  // 使用Vue响应式ref存储消息队列
  private messageQueue = ref<ConsoleMessage[]>([])
  
  private constructor() {}
  
  static getInstance(): ConsoleMessageService {
    if (!this.instance) {
      this.instance = new ConsoleMessageService()
    }
    return this.instance
  }
  
  private getCurrentLocale(): AvailableLocales {
    return localeService.currentLanguage
  }
  
  /**
   * 获取多语言消息
   * 
   * @param category 消息分类（如 'websocket', 'analysis', 'llm' 等）
   * @param key 消息键名
   * @param params 格式化参数
   * @returns 格式化后的消息字符串
   */
  getMessage(category: keyof typeof CONSOLE_MESSAGES['en'], key: string, params?: Record<string, any>): string {
    const currentLocale = this.getCurrentLocale()
    
    // 获取消息模板
    const messages = (CONSOLE_MESSAGES as any)[currentLocale] || CONSOLE_MESSAGES['en']
    const categoryMessages = messages[category] as Record<string, string> || {}
    let messageTemplate = categoryMessages[key] || `[${category}.${key}]`
    
    // 格式化消息
    if (params) {
      try {
        Object.entries(params).forEach(([paramKey, value]) => {
          messageTemplate = messageTemplate.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(value))
        })
      } catch (error) {
        console.warn('Message formatting failed:', error)
      }
    }
    
    return messageTemplate
  }
  
  /**
   * 添加多语言消息到控制台
   * @param type 消息类型
   * @param category 消息分类
   * @param key 消息键名
   * @param params 格式化参数
   * @param agent 可选的智能体名称
   */
  addMessage(
    type: ConsoleMessage['type'], 
    category: keyof typeof CONSOLE_MESSAGES['en'], 
    key: string, 
    params?: Record<string, any>,
    agent?: string
  ) {
    const content = this.getMessage(category, key, params)
    const message: ConsoleMessage = {
      time: new Date().toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
      type,
      content,
      agent
    }
    
    this.messageQueue.value.push(message)
  }
  
  /**
   * 获取消息队列的响应式引用
   * 组件可以订阅这个引用来接收消息更新
   */
  getMessageQueue() {
    return this.messageQueue
  }
  
  /**
   * 清空消息队列
   */
  clearMessages() {
    this.messageQueue.value = []
  }
  
  /**
   * 获取消息数量
   */
  getMessageCount(): number {
    return this.messageQueue.value.length
  }
}

// 导出单例实例
export const consoleMessageService = ConsoleMessageService.getInstance()
export type { ConsoleMessage }