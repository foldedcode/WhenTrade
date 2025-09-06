import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { CostInfo } from '../types/analysis'
import { costApi } from '@/api/cost'
import type { 
  TokenUsageSummary, 
  TokenUsageDetail,
  CostOptimizationSuggestion,
  BudgetSettings as ApiBudgetSettings,
  UserAchievement,
  LeaderboardEntry,
  ModelSelectionStrategy,
  ModelPricing
} from '@/api/cost'
import { useSimpleToast } from '@/composables/useSimpleToast'
import { useAnalysisStore } from '@/stores/analysis'
import { normalizeTokenUsage, estimateTokensFromCost } from '@/utils/tokenNormalizer'

// Provider ID 归一化函数
const normalizeProviderId = (provider: string): string => {
  if (!provider) return ''
  const normalized = provider.toLowerCase().trim()
  // 将 moonshot 归一化为 kimi
  if (normalized === 'moonshot') return 'kimi'
  return normalized
}

// 统一的 provider 提取函数 - 单一真相源
const extractProvider = (record: any): string => {
  // 优先使用规范化的 provider
  if (record.config?.llmProvider) return record.config.llmProvider
  if (record.config?.llm_provider) return record.config.llm_provider
  // 回退：从 config.parameters 查找
  if (record.config?.parameters?.llm_provider) return record.config.parameters.llm_provider
  // 最后尝试从 result 中获取
  if (record.result?._normalized_provider) return record.result._normalized_provider
  return 'unknown' // 明确标记为未知，而不是空字符串
}

export const useCostStore = defineStore('cost', () => {
  const { showError, showSuccess } = useSimpleToast()
  
  // API数据
  const apiLoading = ref(false)
  const usageSummary = ref<TokenUsageSummary | null>(null)
  const usageDetails = ref<TokenUsageDetail[]>([])
  const optimizationSuggestions = ref<CostOptimizationSuggestion[]>([])
  const apiAchievements = ref<UserAchievement[]>([])
  const leaderboard = ref<LeaderboardEntry[]>([])
  const modelPricing = ref<ModelPricing[]>([])
  const availableProviders = ref<string[]>([])
  const modelStrategy = ref<ModelSelectionStrategy>({
    strategy: 'balanced',
    rules: {},
    auto_switch: true
  })
  
  // 成本状态
  const currentCost = ref<CostInfo>({
    totalCost: 0,
    dailyCost: 0,
    monthlyCost: 0,
    budget: {
      daily: 50,
      monthly: 1000
    },
    usage: {
      tokenCount: 0,
      apiCalls: 0
    }
  })

  // 货币汇率（用于统一折算为 USD 展示）
  // 可通过 VITE_CNY_USD_RATE 覆盖，默认 0.14 近似值
  const CNY_TO_USD = Number((import.meta as any).env?.VITE_CNY_USD_RATE || 0.14)

  // 依赖分析历史记录进行实际聚合
  const analysisStore = useAnalysisStore()

  const pricingMap = computed(() => {
    const map = new Map<string, { in: number; out: number; currency: 'USD' | 'CNY' }>()
    for (const p of modelPricing.value) {
      // 兼容后端返回的字段
      const provider = (p as any).provider || ''
      const model = (p as any).model || p.name
      const key = `${provider}:${model}`.toLowerCase()
      const input = (p as any).input_price_per_1k ?? p.input_price
      const output = (p as any).output_price_per_1k ?? p.output_price
      const currency = ((p as any).currency || 'USD').toUpperCase() as 'USD' | 'CNY'
      map.set(key, { in: Number(input) || 0, out: Number(output) || 0, currency })
      // 以模型名作为次要键以增强容错
      map.set(model.toLowerCase(), { in: Number(input) || 0, out: Number(output) || 0, currency })
    }
    return map
  })

  function convertToUSD(amount: number, currency: 'USD' | 'CNY') {
    if (currency === 'USD') return amount
    return amount * CNY_TO_USD
  }

  function recomputeFromHistory() {
    const history = analysisStore.analysisHistory
    let todayTotal = 0
    let monthTotal = 0
    let allTotal = 0
    const providerTotals = new Map<string, { amountUSD: number; currency: 'USD'|'CNY' }>()

    const now = new Date()
    const todayStr = now.toDateString()
    const monthKey = `${now.getFullYear()}-${now.getMonth()}`

    for (const h of history) {
      // 读取 provider/model
      const provider = extractProvider(h)
      const model = (h.config as any)?.llmModel || (h.config as any)?.llm_model || ''
      const key = `${String(provider)}:${String(model)}`.toLowerCase()
      const pricing = pricingMap.value.get(key) || pricingMap.value.get(String(model).toLowerCase())

      // token 使用：使用规范化函数处理多种格式
      const rawUsage = (h as any).result?.token_usage || (h as any).usage || (h as any).result?.usage
      const normalizedUsage = normalizeTokenUsage(rawUsage)
      let inTokens = normalizedUsage.inputTokens
      let outTokens = normalizedUsage.outputTokens

      let usdCost: number
      if (pricing && (inTokens > 0 || outTokens > 0)) {
        const localCost = (inTokens / 1000) * pricing.in + (outTokens / 1000) * pricing.out
        usdCost = convertToUSD(localCost, pricing.currency)
      } else if (typeof h.cost === 'number' && h.cost > 0) {
        // 兼容旧记录：直接使用保存的 cost（默认当作 USD）
        usdCost = Number(h.cost)
        
        // 如果有成本但没有 tokens，尝试反推
        if (inTokens === 0 && outTokens === 0 && pricing) {
          const estimatedUsage = estimateTokensFromCost(h.cost, pricing)
          inTokens = estimatedUsage.inputTokens
          outTokens = estimatedUsage.outputTokens
        }
      } else {
        usdCost = 0
      }

      allTotal += usdCost

      // provider 汇总（使用提供商默认币种显示：USD/CNY）
      const defaultCurrency = (key.startsWith('deepseek') || key.startsWith('kimi')) ? 'CNY' : 'USD'
      const rec = providerTotals.get(provider) || { amountUSD: 0, currency: defaultCurrency as 'USD'|'CNY' }
      rec.amountUSD += usdCost
      providerTotals.set(String(provider), rec)

      const dt = new Date(h.timestamp)
      if (dt.toDateString() === todayStr) todayTotal += usdCost
      const mk = `${dt.getFullYear()}-${dt.getMonth()}`
      if (mk === monthKey) monthTotal += usdCost
    }

    currentCost.value.dailyCost = Number(todayTotal.toFixed(3))
    currentCost.value.monthlyCost = Number(monthTotal.toFixed(3))
    currentCost.value.totalCost = Number(allTotal.toFixed(3))

    _perProviderTotals.value = providerTotals
  }

  // 按提供商的聚合（USD），并提供格式化显示（¥/$）
  const _perProviderTotals = ref(new Map<string, { amountUSD: number; currency: 'USD'|'CNY' }>())
  const providerUsage = computed(() => {
    const items: Array<{ id: string; label: string; amountText: string }> = []
    const symbol: Record<'USD'|'CNY', string> = { USD: '$', CNY: '¥' }
    for (const id of availableProviders.value) {
      const rec = _perProviderTotals.value.get(id)
      if (!rec) continue
      const amountLocal = rec.currency === 'USD' ? rec.amountUSD : rec.amountUSD / (CNY_TO_USD || 0.14)
      const amountText = `${symbol[rec.currency]}${amountLocal.toFixed(2)}`
      const labelMap: Record<string, string> = { openai: 'OpenAI', google: 'Google', deepseek: 'DeepSeek', kimi: 'Moonshot' }
      items.push({ id, label: labelMap[id] || id, amountText })
    }
    return items
  })

  // 格式化大数字（如token数量）
  function formatNumber(num: number): string {
    if (num >= 1000000) return `${(num/1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num/1000).toFixed(1)}K`
    return num.toString()
  }

  // 获取提供商显示名称
  function getProviderLabel(provider: string, model: string): string {
    const map: Record<string, string> = {
      'openai': 'OpenAI',
      'google': 'Google',
      'anthropic': 'Claude',
      'deepseek': 'DeepSeek',
      'kimi': 'Moonshot',
      'moonshot': 'Moonshot'
    }
    
    const baseLabel = map[provider.toLowerCase()] || provider
    
    // 为特定模型添加后缀
    if (model) {
      if (model.includes('gpt-4')) return `${baseLabel} GPT-4`
      if (model.includes('gpt-3.5')) return `${baseLabel} GPT-3.5`
      if (model.includes('claude-3-opus')) return `${baseLabel} 3 Opus`
      if (model.includes('claude-3-sonnet')) return `${baseLabel} 3 Sonnet`
      if (model.includes('gemini')) return `${baseLabel} Gemini`
    }
    
    return baseLabel
  }

  // 新的按提供商统计token和成本
  const providerStats = computed(() => {
    const stats = new Map<string, {
      id: string
      label: string
      inputTokens: number
      outputTokens: number  
      totalTokens: number
      cost: number
      currency: 'USD' | 'CNY'
    }>()
    
    // 首先初始化所有可用的提供商（显示为0）
    for (const providerId of availableProviders.value) {
      const normalizedId = normalizeProviderId(providerId)
      // 确定货币类型（基于归一化后的提供商）
      const currency: 'USD' | 'CNY' = (['deepseek', 'kimi'].includes(normalizedId)) ? 'CNY' : 'USD'
      
      stats.set(normalizedId, {
        id: normalizedId,
        label: getProviderLabel(providerId, ''),
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        cost: 0,
        currency
      })
    }
    
    // 然后累加历史使用数据
    const history = analysisStore.analysisHistory
    
    for (const h of history) {
      const originalProvider = extractProvider(h)
      const provider = normalizeProviderId(originalProvider)
      
      // 如果 stats 中没有这个 provider，创建它（处理未知或新的 provider）
      if (provider && !stats.has(provider)) {
        const currency: 'USD' | 'CNY' = (['deepseek', 'kimi'].includes(provider)) ? 'CNY' : 'USD'
        stats.set(provider, {
          id: provider,
          label: getProviderLabel(provider, ''),
          inputTokens: 0,
          outputTokens: 0,
          totalTokens: 0,
          cost: 0,
          currency
        })
      }
      const model = (h.config as any)?.llmModel || (h.config as any)?.llm_model || ''
      const key = `${provider}:${model}`.toLowerCase()
      
      // 获取token使用量 - 使用规范化函数处理多种格式
      const rawUsage = (h as any).result?.token_usage || (h as any).usage || (h as any).result?.usage
      const normalizedUsage = normalizeTokenUsage(rawUsage)
      let inputTokens = normalizedUsage.inputTokens
      let outputTokens = normalizedUsage.outputTokens
      let totalTokens = normalizedUsage.totalTokens
      
      // 获取定价信息
      const pricing = pricingMap.value.get(key) || pricingMap.value.get(String(model).toLowerCase())
      
      let cost = 0
      
      if (pricing && totalTokens > 0) {
        cost = (inputTokens / 1000) * pricing.in + (outputTokens / 1000) * pricing.out
      } else if (typeof h.cost === 'number' && h.cost > 0) {
        // 兼容旧记录：直接使用保存的cost
        cost = Number(h.cost)
        
        // 如果有成本但没有 tokens，尝试反推
        if (totalTokens === 0 && pricing) {
          const estimatedUsage = estimateTokensFromCost(cost, pricing)
          inputTokens = estimatedUsage.inputTokens
          outputTokens = estimatedUsage.outputTokens
          totalTokens = estimatedUsage.totalTokens
          
        }
      }
      
      // 累加到对应提供商的统计中（使用归一化后的provider）
      let existing = stats.get(provider)
      if (!existing && provider) {
        // 如果统计中没有这个provider，创建一个新条目
        const currency: 'USD' | 'CNY' = (['deepseek', 'kimi'].includes(provider)) ? 'CNY' : 'USD'
        existing = {
          id: provider,
          label: getProviderLabel(originalProvider, ''),
          inputTokens: 0,
          outputTokens: 0,
          totalTokens: 0,
          cost: 0,
          currency
        }
        stats.set(provider, existing)
      }
      
      if (existing) {
        existing.inputTokens += inputTokens
        existing.outputTokens += outputTokens
        existing.totalTokens += totalTokens
        existing.cost += cost
      } else if ((cost > 0 || totalTokens > 0) && provider === 'unknown') {
        // 对未知 provider 创建特殊条目
        if (!stats.has('unknown')) {
          stats.set('unknown', {
            id: 'unknown',
            label: '未知提供商（历史数据）',
            inputTokens: 0,
            outputTokens: 0,
            totalTokens: 0,
            cost: 0,
            currency: 'USD'
          })
        }
        const unknown = stats.get('unknown')!
        unknown.inputTokens += inputTokens
        unknown.outputTokens += outputTokens
        unknown.totalTokens += totalTokens
        unknown.cost += cost
      }
    }
    
    return Array.from(stats.values())
      .map(s => ({
        ...s,
        formattedTokens: s.totalTokens > 0 ? formatNumber(s.totalTokens) : '0',
        formattedCost: `${s.currency === 'CNY' ? '¥' : '$'}${s.cost.toFixed(3)}`
      }))
  })

  // 成本历史记录
  const costHistory = ref<Array<{
    date: string
    cost: number
    type: 'analysis' | 'api_call' | 'token_usage'
    description: string
  }>>([])

  // 预算告警设置
  const alertSettings = ref({
    dailyThreshold: 0.8, // 80%预算时告警
    monthlyThreshold: 0.9, // 90%预算时告警
    enableAlerts: true
  })

  // 游戏化元素
  const gamification = ref({
    level: 1,
    experience: 0,
    achievements: [] as Array<{
      id: string
      name: string
      description: string
      unlockedAt: string
      icon: string
    }>,
    badges: [] as Array<{
      id: string
      name: string
      type: 'cost_saver' | 'efficiency' | 'analysis_master'
      earnedAt: string
    }>,
    streak: {
      current: 0,
      best: 0,
      type: 'under_budget_days'
    }
  })

  // 计算属性
  const totalCost = computed(() => currentCost.value.totalCost)
  
  const dailyBudgetUsage = computed(() => {
    return currentCost.value.budget.daily > 0 
      ? (currentCost.value.dailyCost / currentCost.value.budget.daily) * 100 
      : 0
  })

  const monthlyBudgetUsage = computed(() => {
    return currentCost.value.budget.monthly > 0 
      ? (currentCost.value.monthlyCost / currentCost.value.budget.monthly) * 100 
      : 0
  })

  const isDailyBudgetExceeded = computed(() => {
    return currentCost.value.dailyCost > currentCost.value.budget.daily
  })

  const isMonthlyBudgetExceeded = computed(() => {
    return currentCost.value.monthlyCost > currentCost.value.budget.monthly
  })

  const shouldShowDailyAlert = computed(() => {
    return alertSettings.value.enableAlerts && 
           dailyBudgetUsage.value >= alertSettings.value.dailyThreshold * 100
  })

  const shouldShowMonthlyAlert = computed(() => {
    return alertSettings.value.enableAlerts && 
           monthlyBudgetUsage.value >= alertSettings.value.monthlyThreshold * 100
  })

  const costEfficiencyScore = computed(() => {
    // 基于成本控制和分析质量计算效率分数
    const budgetEfficiency = Math.max(0, 100 - Math.max(dailyBudgetUsage.value, monthlyBudgetUsage.value))
    const usageEfficiency = currentCost.value.usage.apiCalls > 0 
      ? (currentCost.value.usage.tokenCount / currentCost.value.usage.apiCalls) / 1000 * 100
      : 100
    
    return Math.min(100, (budgetEfficiency + usageEfficiency) / 2)
  })

  const nextLevelProgress = computed(() => {
    const currentLevelExp = gamification.value.level * 1000
    const nextLevelExp = (gamification.value.level + 1) * 1000
    const progress = ((gamification.value.experience - currentLevelExp) / (nextLevelExp - currentLevelExp)) * 100
    return Math.max(0, Math.min(100, progress))
  })

  const currentSessionCost = computed(() => {
    // 计算当前会话的成本（可以基于最近的分析）
    const today = new Date().toDateString()
    const todayCosts = costHistory.value.filter(item => 
      new Date(item.date).toDateString() === today
    )
    return todayCosts.reduce((sum, item) => sum + item.cost, 0)
  })

  const remainingBudget = computed(() => {
    return Math.max(0, currentCost.value.budget.daily - currentCost.value.dailyCost)
  })
  
  const totalTokens = computed(() => {
    return usageSummary.value?.total_tokens || currentCost.value.usage.tokenCount
  })
  
  const totalPotentialSavings = computed(() => {
    return optimizationSuggestions.value
      .filter(s => !s.is_implemented)
      .reduce((sum, s) => sum + s.potential_savings, 0)
  })
  
  const unimplementedSuggestions = computed(() => {
    return optimizationSuggestions.value.filter(s => !s.is_implemented).length
  })

  // Actions
  const addCost = (amount: number, type: 'analysis' | 'api_call' | 'token_usage', description: string) => {
    currentCost.value.totalCost += amount
    currentCost.value.dailyCost += amount
    currentCost.value.monthlyCost += amount

    // 更新使用统计
    if (type === 'api_call') {
      currentCost.value.usage.apiCalls += 1
    } else if (type === 'token_usage') {
      currentCost.value.usage.tokenCount += Math.floor(amount * 100) // 假设每分钱100 tokens
    }

    // 添加到历史记录
    costHistory.value.unshift({
      date: new Date().toISOString(),
      cost: amount,
      type,
      description
    })

    // 更新游戏化元素
    updateGamification(amount, type)
    
    // 保存到本地存储
    saveToLocalStorage()
  }

  const updateGamification = (_costAmount: number, _type: string) => {
    // 增加经验值（成本控制得越好，经验值越高）
    const efficiencyBonus = costEfficiencyScore.value / 100
    const baseExp = 10
    const expGained = Math.floor(baseExp * efficiencyBonus)
    
    gamification.value.experience += expGained

    // 检查升级
    const requiredExp = gamification.value.level * 1000
    if (gamification.value.experience >= requiredExp) {
      gamification.value.level += 1
      
      // 解锁成就
      unlockAchievement({
        id: `level_${gamification.value.level}`,
        name: `等级 ${gamification.value.level}`,
        description: `达到等级 ${gamification.value.level}`,
        unlockedAt: new Date().toISOString(),
        icon: '🏆'
      })
    }

    // 检查预算控制成就
    if (!isDailyBudgetExceeded.value && currentCost.value.dailyCost > 0) {
      gamification.value.streak.current += 1
      if (gamification.value.streak.current > gamification.value.streak.best) {
        gamification.value.streak.best = gamification.value.streak.current
      }

      // 连续控制预算成就
      if (gamification.value.streak.current === 7) {
        unlockAchievement({
          id: 'budget_master_week',
          name: '预算大师',
          description: '连续7天控制在预算内',
          unlockedAt: new Date().toISOString(),
          icon: '💰'
        })
      }
    } else if (isDailyBudgetExceeded.value) {
      gamification.value.streak.current = 0
    }

    // 效率徽章
    if (costEfficiencyScore.value >= 90 && !gamification.value.badges.find(b => b.id === 'efficiency_expert')) {
      gamification.value.badges.push({
        id: 'efficiency_expert',
        name: '效率专家',
        type: 'efficiency',
        earnedAt: new Date().toISOString()
      })
    }
  }

  const unlockAchievement = (achievement: typeof gamification.value.achievements[0]) => {
    if (!gamification.value.achievements.find(a => a.id === achievement.id)) {
      gamification.value.achievements.push(achievement)
    }
  }

  const setBudget = async (daily: number, monthly: number) => {
    currentCost.value.budget.daily = daily
    currentCost.value.budget.monthly = monthly
    saveToLocalStorage()
    await updateApiBudgetSettings()
  }

  const resetDailyCost = () => {
    currentCost.value.dailyCost = 0
    saveToLocalStorage()
  }

  const resetMonthlyCost = () => {
    currentCost.value.monthlyCost = 0
    currentCost.value.dailyCost = 0
    saveToLocalStorage()
  }

  const updateAlertSettings = (settings: Partial<typeof alertSettings.value>) => {
    alertSettings.value = { ...alertSettings.value, ...settings }
    saveToLocalStorage()
  }

  const clearCostHistory = () => {
    costHistory.value = []
    saveToLocalStorage()
  }

  const resetUserData = () => {
    // 重置所有用户数据为初始状态
    currentCost.value = {
      totalCost: 0,
      dailyCost: 0,
      monthlyCost: 0,
      budget: {
        daily: 50,
        monthly: 1000
      },
      usage: {
        tokenCount: 0,
        apiCalls: 0
      }
    }
    costHistory.value = []
    gamification.value = {
      level: 1,
      experience: 0,
      achievements: [],
      badges: [],
      streak: {
        current: 0,
        best: 0,
        type: 'under_budget_days'
      }
    }
  }

  const getCostTrend = (days: number = 7) => {
    const now = new Date()
    const startDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
    
    return costHistory.value
      .filter(entry => new Date(entry.date) >= startDate)
      .reduce((acc, entry) => {
        const date = entry.date.split('T')[0]
        acc[date] = (acc[date] || 0) + entry.cost
        return acc
      }, {} as Record<string, number>)
  }

  const updateDailyBudget = async (budget: number) => {
    currentCost.value.budget.daily = budget
    saveToLocalStorage()
    await updateApiBudgetSettings()
  }

  const updateMonthlyBudget = async (budget: number) => {
    currentCost.value.budget.monthly = budget
    saveToLocalStorage()
    await updateApiBudgetSettings()
  }

  const initMockData = () => {
    // 新用户不需要模拟数据
    return
    /* 注释掉原有的模拟数据生成逻辑
    // 初始化一些基础成本数据
    if (currentCost.value.dailyCost === 0) {
      currentCost.value.dailyCost = 8.25
      currentCost.value.monthlyCost = 156.78
      currentCost.value.totalCost = 1247.32
    }
    */
  }

  const generateMockCostData = () => {
    // 生成模拟成本数据用于演示
    const mockEntries = [
      { cost: 2.5, type: 'analysis' as const, description: 'BTC/USDT 深度分析' },
      { cost: 1.2, type: 'api_call' as const, description: '市场数据获取' },
      { cost: 0.8, type: 'token_usage' as const, description: 'GPT-4 tokens' },
      { cost: 3.1, type: 'analysis' as const, description: 'ETH/USDT 技术分析' },
      { cost: 0.5, type: 'api_call' as const, description: '情绪数据分析' }
    ]

    mockEntries.forEach((entry, index) => {
      setTimeout(() => {
        addCost(entry.cost, entry.type, entry.description)
      }, index * 1000)
    })
  }

  const saveToLocalStorage = () => {
    try {
      // 添加用户ID前缀，确保数据隔离
      const userId = 'default-user'
      if (!userId) return
      
      const key = `cost_data_${userId}`
      localStorage.setItem(key, JSON.stringify({
        currentCost: currentCost.value,
        costHistory: costHistory.value.slice(0, 100), // 只保存最近100条记录
        alertSettings: alertSettings.value,
        gamification: gamification.value
      }))
    } catch (err) {
      // 无法保存成本数据到本地存储
    }
  }

  const loadFromLocalStorage = () => {
    try {
      // 使用用户ID前缀加载数据
      const userId = 'default-user'
      if (!userId) {
        // 未登录时重置数据
        resetUserData()
        return
      }
      
      const key = `cost_data_${userId}`
      const saved = localStorage.getItem(key)
      
      if (saved) {
        const data = JSON.parse(saved)
        currentCost.value = { ...currentCost.value, ...data.currentCost }
        costHistory.value = data.costHistory || []
        alertSettings.value = { ...alertSettings.value, ...data.alertSettings }
        gamification.value = { ...gamification.value, ...data.gamification }
      } else {
        // 尝试迁移旧数据（一次性）
        const oldData = localStorage.getItem('cost_data')
        if (oldData) {
          try {
            const data = JSON.parse(oldData)
            currentCost.value = { ...currentCost.value, ...data.currentCost }
            costHistory.value = data.costHistory || []
            alertSettings.value = { ...alertSettings.value, ...data.alertSettings }
            gamification.value = { ...gamification.value, ...data.gamification }
            saveToLocalStorage() // 保存到新的key
            localStorage.removeItem('cost_data') // 删除旧数据
          } catch {
            // 旧数据损坏，清理
            localStorage.removeItem('cost_data')
          }
        } else {
          // 新用户，重置数据
          resetUserData()
        }
      }
    } catch (err) {
      // 无法从本地存储加载成本数据
      resetUserData()
    }
  }

  // 简化版本无需监听登录状态

  // 初始化时加载数据
  loadFromLocalStorage()
  
  // API方法
  const fetchUsageSummary = async (days: number = 30) => {
    apiLoading.value = true
    try {
      const response = await costApi.getUsageSummary(days)
      // 检查响应结构
      if (!response || typeof response !== 'object') {
        throw new Error('Invalid response format')
      }
      
      usageSummary.value = response.data || response
      
      // 更新本地成本数据
      const data = response.data || response
      if (data && typeof data === 'object') {
        currentCost.value.totalCost = data.total_cost || 0
        currentCost.value.dailyCost = data.daily_average || 0
        // 估算月度成本
        currentCost.value.monthlyCost = (data.daily_average || 0) * 30
      }
    } catch (error: any) {
      // 详细的错误处理
      if (error?.message?.includes('HTTP 500')) {
        showError('服务器错误：成本服务暂时不可用')
      } else if (error?.message?.includes('HTTP 401')) {
        showError('认证失败：请重新登录')
      } else if (error?.message?.includes('Network')) {
        showError('网络错误：请检查网络连接')
      } else {
        showError('获取使用情况汇总失败')
      }
      console.error('Failed to fetch usage summary:', error)
      
      // 设置默认值避免界面错误
      usageSummary.value = null
    } finally {
      apiLoading.value = false
    }
  }
  
  const fetchUsageDetails = async (params: { start_date?: string; end_date?: string; model?: string; limit?: number }) => {
    try {
      const response = await costApi.getUsageDetails(params)
      usageDetails.value = response.data || []
    } catch (error: any) {
      if (error?.message?.includes('HTTP 500')) {
        showError('服务器错误：无法获取使用详情')
      } else {
        showError('获取使用详情失败')
      }
      console.error('Failed to fetch usage details:', error)
      usageDetails.value = []
    }
  }
  
  const fetchOptimizationSuggestions = async () => {
    try {
      const response = await costApi.getOptimizationSuggestions()
      optimizationSuggestions.value = response.data || []
    } catch (error: any) {
      if (error?.message?.includes('HTTP 500')) {
        showError('服务器错误：优化建议服务暂时不可用')
      } else {
        showError('获取优化建议失败')
      }
      console.error('Failed to fetch optimization suggestions:', error)
      optimizationSuggestions.value = []
    }
  }
  
  const fetchBudgetSettings = async () => {
    try {
      const response = await costApi.getBudgetSettings()
      const data = response.data || response
      if (data && typeof data === 'object') {
        currentCost.value.budget.daily = data.daily_limit || 50
        currentCost.value.budget.monthly = data.monthly_limit || 1000
        alertSettings.value.dailyThreshold = data.alert_threshold || 0.8
        alertSettings.value.monthlyThreshold = data.alert_threshold || 0.9
      }
    } catch (error: any) {
      if (error?.message?.includes('HTTP 500')) {
        showError('服务器错误：预算设置服务暂时不可用')
        // 使用本地存储的设置
        console.log('Using local budget settings due to server error')
      } else {
        showError('获取预算设置失败')
      }
      console.error('Failed to fetch budget settings:', error)
    }
  }
  
  const updateApiBudgetSettings = async () => {
    try {
      const settings: ApiBudgetSettings = {
        daily_limit: currentCost.value.budget.daily,
        monthly_limit: currentCost.value.budget.monthly,
        alert_threshold: alertSettings.value.dailyThreshold
      }
      await costApi.updateBudgetSettings(settings)
      showSuccess('预算设置已更新')
    } catch (error) {
      showError('更新预算设置失败')
      console.error('Failed to update budget settings:', error)
    }
  }
  
  const fetchAchievements = async () => {
    try {
      const response = await costApi.getAchievements()
      apiAchievements.value = response.data
    } catch (error) {
      showError('获取成就列表失败')
      console.error('Failed to fetch achievements:', error)
    }
  }
  
  const fetchLeaderboard = async (timeframe: 'daily' | 'weekly' | 'monthly' | 'all_time' = 'monthly') => {
    try {
      const response = await costApi.getLeaderboard(timeframe)
      leaderboard.value = response.data
    } catch (error) {
      showError('获取排行榜失败')
      console.error('Failed to fetch leaderboard:', error)
    }
  }
  
  const fetchModelPricing = async () => {
    try {
      const response = await costApi.getModelPricing()
      
      // 验证响应结构
      if (!response) {
        console.warn('Model pricing API returned empty response')
        modelPricing.value = []
        return
      }
      
      // 检查 models 字段（直接在response根级别）
      if (!response.models || !Array.isArray(response.models)) {
        console.warn('Model pricing response missing valid models array:', response)
        modelPricing.value = []
        return
      }
      
      // 设置模型定价数据
      modelPricing.value = response.models
      console.log(`✅ Successfully loaded ${response.models.length} model pricing entries`)
      
    } catch (error) {
      // 详细的错误处理
      modelPricing.value = []
      
      if (error instanceof Error) {
        console.warn('Failed to fetch model pricing:', {
          message: error.message,
          name: error.name
        })
        
        // 静默处理错误，不显示toast（避免干扰用户）
        // 模型定价失败不影响核心功能，只是无法显示精确成本
      } else {
        console.warn('Failed to fetch model pricing:', error)
      }
    }
  }
  
  const fetchModelStrategy = async () => {
    try {
      const response = await costApi.getModelStrategy()
      modelStrategy.value = response.data
    } catch (error) {
      showError('获取模型策略失败')
      console.error('Failed to fetch model strategy:', error)
    }
  }
  
  const updateModelStrategy = async (strategy: ModelSelectionStrategy) => {
    try {
      const response = await costApi.updateModelStrategy(strategy)
      modelStrategy.value = response.data
      showSuccess('模型选择策略已更新')
    } catch (error) {
      showError('更新模型策略失败')
      console.error('Failed to update model strategy:', error)
    }
  }
  
  const applyOptimizationSuggestion = async (suggestionId: string) => {
    try {
      const response = await costApi.autoApplyOptimization(suggestionId)
      if (response.data.applied) {
        showSuccess(response.data.message)
        // 重新获取优化建议和模型策略
        await Promise.all([
          fetchOptimizationSuggestions(),
          fetchModelStrategy()
        ])
      } else {
        showError(response.data.message)
      }
    } catch (error) {
      showError('应用优化建议失败')
      console.error('Failed to apply optimization:', error)
    }
  }
  
  const initializeApiData = async () => {
    // 只调用真正需要的API，避免404错误
    const results = await Promise.allSettled([
      fetchModelPricing()  // 只保留模型定价API
    ])
    
    // 统计失败的请求
    const failures = results.filter(r => r.status === 'rejected').length
    if (failures > 0) {
      console.warn(`${failures} API requests failed during initialization`)
      if (failures === results.length) {
        console.warn('模型定价服务不可用，将使用历史数据')
      }
    }
    
    // 加载可用提供商
    try {
      const resp = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/llm/providers/available`)
      if (resp.ok) {
        const data = await resp.json()
        availableProviders.value = (data.providers || []).map((p: any) => p.id)
        console.log('✅ 已加载可用提供商:', availableProviders.value)
      }
    } catch (error) {
      console.warn('加载提供商列表失败:', error)
    }
    
    // 初始价格加载后计算一次
    recomputeFromHistory()
  }

  // 监控分析历史与定价变动，实时回填成本卡片
  watch(
    () => [analysisStore.analysisHistory, modelPricing.value],
    () => recomputeFromHistory(),
    { deep: true }
  )

  return {
    // State
    currentCost,
    costHistory,
    alertSettings,
    gamification,
    
    // API State
    apiLoading,
    usageSummary,
    usageDetails,
    optimizationSuggestions,
    apiAchievements,
    leaderboard,
    modelPricing,
    modelStrategy,

    // Computed
    totalCost,
    totalTokens,
    totalPotentialSavings,
    unimplementedSuggestions,
    dailyBudgetUsage,
    monthlyBudgetUsage,
    isDailyBudgetExceeded,
    isMonthlyBudgetExceeded,
    shouldShowDailyAlert,
    shouldShowMonthlyAlert,
    costEfficiencyScore,
    nextLevelProgress,
    currentSessionCost,
    remainingBudget,

    // Actions
    addCost,
    setBudget,
    updateDailyBudget,
    updateMonthlyBudget,
    resetDailyCost,
    resetMonthlyCost,
    updateAlertSettings,
    clearCostHistory,
    getCostTrend,
    initMockData,
    generateMockCostData,
    loadFromLocalStorage,
    
    // API Actions
    fetchUsageSummary,
    fetchUsageDetails,
    fetchOptimizationSuggestions,
    fetchBudgetSettings,
    updateApiBudgetSettings,
    fetchAchievements,
    fetchLeaderboard,
    fetchModelPricing,
    fetchModelStrategy,
    updateModelStrategy,
    applyOptimizationSuggestion,
    initializeApiData,
    
    // Provider Stats
    providerStats
  }
}) 
