/**
 * 统一的执行阶段定义
 * 消除前后端阶段名称不一致的特殊情况
 */

import { createI18n } from 'vue-i18n'

// 导入翻译文件
import zhAnalysis from '@/locales/zh-CN/analysis.json'
import enAnalysis from '@/locales/en-US/analysis.json'

// 创建专用的 i18n 实例
const phaseI18n = createI18n({
  locale: localStorage.getItem('when-trade-locale') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': { analysis: zhAnalysis },
    'en-US': { analysis: enAnalysis }
  }
})

// 获取翻译文本的辅助函数
const getTeamTranslation = (teamId: string): string => {
  const locale = localStorage.getItem('when-trade-locale') || 'zh-CN'
  // 动态更新i18n实例的locale
  phaseI18n.global.locale = locale
  const t = phaseI18n.global.t
  return t(`analysis.teams.${teamId}`) as string
}

export interface ExecutionPhase {
  id: string           // 前端使用的阶段ID
  backendKey: string   // 后端使用的阶段key
  name: string         // 显示名称
  order: number        // 执行顺序（1-5）
  parallel: boolean    // 阶段内节点是否可并行
  nodes?: string[]     // 该阶段包含的节点
  getName: () => string // 动态获取翻译名称
}

export const EXECUTION_PHASES: Record<string, ExecutionPhase> = {
  phase1_analysis: {
    id: 'analyst',
    backendKey: 'phase1_analysis',
    name: '数据分析', // 保留作为fallback
    order: 1,
    parallel: true,
    nodes: ['Market Analyst', 'Social Media Analyst', 'News Analyst', 'Fundamentals Analyst', 'Onchain Analyst', 'DeFi Analyst'],
    getName: () => getTeamTranslation('analyst')
  },
  phase2_debate: {
    id: 'research',
    backendKey: 'phase2_debate', 
    name: '投资辩论', // 保留作为fallback
    order: 2,
    parallel: false,  // 第二阶段是串行的：Bull → Bear → Research Manager
    nodes: ['Bull Researcher', 'Bear Researcher', 'Research Manager'],
    getName: () => getTeamTranslation('research')
  },
  phase3_trading: {
    id: 'trading',
    backendKey: 'phase3_trading',
    name: '交易策略', // 保留作为fallback
    order: 3,
    parallel: false,
    nodes: ['Trader'],
    getName: () => getTeamTranslation('trading')
  },
  phase4_risk: {
    id: 'risk',
    backendKey: 'phase4_risk',
    name: '风险评估', // 保留作为fallback
    order: 4,
    parallel: false,  // 第四阶段串行执行：Risky → Safe → Neutral → Risk Judge
    nodes: ['Risky Analyst', 'Safe Analyst', 'Neutral Analyst', 'Risk Judge'],
    getName: () => getTeamTranslation('risk')
  },
  phase5_decision: {
    id: 'portfolio',
    backendKey: 'phase5_decision',
    name: '组合管理', // 保留作为fallback
    order: 5,
    parallel: false,
    nodes: ['Portfolio Manager'],
    getName: () => getTeamTranslation('portfolio')
  }
}

// 后端phase key到前端stage的映射
export const phaseToStageMap: Record<string, string> = Object.values(EXECUTION_PHASES).reduce((acc, phase) => {
  acc[phase.backendKey] = phase.id
  return acc
}, {} as Record<string, string>)

// 前端stage到phase信息的映射
export const stageToPhaseMap: Record<string, ExecutionPhase> = Object.values(EXECUTION_PHASES).reduce((acc, phase) => {
  acc[phase.id] = phase
  return acc
}, {} as Record<string, ExecutionPhase>)

// 获取阶段显示名称
export function getPhaseDisplayName(stageOrPhase: string): string {
  // 尝试从stage ID获取
  if (stageToPhaseMap[stageOrPhase]) {
    return stageToPhaseMap[stageOrPhase].getName()
  }
  
  // 尝试从backend key获取
  if (EXECUTION_PHASES[stageOrPhase]) {
    return EXECUTION_PHASES[stageOrPhase].getName()
  }
  
  // 如果都找不到，尝试直接翻译
  try {
    return getTeamTranslation(stageOrPhase)
  } catch {
    return stageOrPhase
  }
}

// 获取阶段执行顺序
export function getPhaseOrder(stageOrPhase: string): number {
  // 尝试从stage ID获取
  if (stageToPhaseMap[stageOrPhase]) {
    return stageToPhaseMap[stageOrPhase].order
  }
  
  // 尝试从backend key获取
  if (EXECUTION_PHASES[stageOrPhase]) {
    return EXECUTION_PHASES[stageOrPhase].order
  }
  
  return 0
}