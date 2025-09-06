/**
 * 分析报告生成工具
 * 极简版本：只保留必要的向后兼容接口
 */

// 为向后兼容保留的空函数
export const generateMarkdownReport = (_reportData: any): string => {
  return '此功能已重构，请使用新的SimpleReport组件'
}

export const generateReportFromHistory = (history: any): any => {
  return {
    config: history?.config || {},
    analysis: { timestamp: history?.timestamp || Date.now() },
    insights: {},
    marketInfo: {},
    riskAssessment: {},
    conclusion: {},
    agentContributions: []
  }
}

export const generateSimpleMarkdownReport = (_history: any): string => {
  return '此功能已重构，请使用新的SimpleReport组件'
}

// 旧的ReportData接口保留用于类型兼容
export interface ReportData {
  config: any
  analysis: any
  insights: any
  marketInfo: any
  riskAssessment: any
  conclusion: any
  agentContributions: any[]
  technicalIndicators?: string
}