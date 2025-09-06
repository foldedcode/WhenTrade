/**
 * Token 使用量规范化工具
 * 统一处理各种 LLM provider 的不同 token 字段格式
 */

export interface TokenUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

/**
 * 检查对象是否包含 usage 相关字段
 */
const hasUsageFields = (obj: any): boolean => {
  if (!obj || typeof obj !== 'object') return false
  
  const usageKeys = [
    'total_tokens', 'totalTokens', 'bill_tokens', 'billTokens',
    'prompt_tokens', 'completion_tokens', 'input_tokens', 'output_tokens',
    'promptTokens', 'completionTokens', 'inputTokens', 'outputTokens',
    'usage', 'token_usage'
  ]
  
  return Object.keys(obj).some(key => usageKeys.includes(key))
}

/**
 * 检查是否为业务结果对象
 */
const isBusinessResult = (obj: any): boolean => {
  if (!obj || typeof obj !== 'object') return false
  
  const businessKeys = [
    'company', 'date', 'signal', 'analysis', 'sentiment',
    'type', 'result', 'insights', 'recommendations'
  ]
  
  return businessKeys.some(key => key in obj)
}

/**
 * 规范化 token 使用量数据
 * 支持所有已知的字段格式：OpenAI、Google、DeepSeek、Moonshot等
 * 
 * @param usage 原始的 usage 数据对象
 * @returns 规范化后的 token 使用量
 */
export const normalizeTokenUsage = (usage: any): TokenUsage => {
  // 快速返回：非对象
  if (!usage || typeof usage !== 'object') {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
  }
  
  // 识别业务结果对象，静默跳过
  if (isBusinessResult(usage)) {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
  }
  
  // 只对包含 usage 相关字段的对象进行处理
  if (!hasUsageFields(usage)) {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
  }
  
  // 统一所有可能的输入 token 字段名
  const inputTokens = Number(
    usage.input_tokens ||
    usage.prompt_tokens ||
    usage.inputTokens ||
    usage.promptTokens ||
    usage.total_input_tokens ||
    usage.input ||
    usage.prompt ||
    usage.in ||
    0
  )
  
  // 统一所有可能的输出 token 字段名
  const outputTokens = Number(
    usage.output_tokens ||
    usage.completion_tokens ||
    usage.outputTokens ||
    usage.completionTokens ||
    usage.total_output_tokens ||
    usage.output ||
    usage.completion ||
    usage.out ||
    0
  )
  
  // 如果有明确的输入输出值，直接使用
  if (inputTokens > 0 || outputTokens > 0) {
    return {
      inputTokens,
      outputTokens,
      totalTokens: inputTokens + outputTokens
    }
  }
  
  // 如果只有总量，尝试按比例分配
  const explicitTotal = Number(
    usage.total_tokens ||
    usage.totalTokens ||
    usage.total ||
    usage.bill_tokens ||
    usage.billTokens ||
    0
  )
  
  if (explicitTotal > 0) {
    // 按经验比例分配（输入:输出 = 3:1，适用于大多数分析场景）
    const estimatedInput = Math.floor(explicitTotal * 0.75)
    const estimatedOutput = explicitTotal - estimatedInput
    return {
      inputTokens: estimatedInput,
      outputTokens: estimatedOutput,
      totalTokens: explicitTotal
    }
  }
  
  // 完全没有 token 数据
  return { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
}

/**
 * 基于成本和定价信息反推 token 使用量
 * 用于历史数据中只有成本但缺少 token 统计的情况
 * 
 * @param cost 成本金额
 * @param pricing 定价信息 {in: 输入价格, out: 输出价格}
 * @returns 估算的 token 使用量
 */
export const estimateTokensFromCost = (
  cost: number, 
  pricing: { in: number; out: number }
): TokenUsage => {
  if (cost <= 0 || !pricing || (pricing.in === 0 && pricing.out === 0)) {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
  }
  
  // 使用平均价格计算总 token 数
  const avgPrice = (pricing.in + pricing.out) / 2
  const estimatedTotal = Math.round((cost / avgPrice) * 1000)
  
  if (estimatedTotal <= 0) {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 }
  }
  
  // 按经验比例分配
  const estimatedInput = Math.floor(estimatedTotal * 0.75)
  const estimatedOutput = estimatedTotal - estimatedInput
  
  return {
    inputTokens: estimatedInput,
    outputTokens: estimatedOutput,
    totalTokens: estimatedTotal
  }
}