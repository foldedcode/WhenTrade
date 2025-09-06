/**
 * 数据相关类型定义
 */

export interface PriceData {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  symbol?: string
}

export interface QuoteData {
  symbol: string
  price: number
  change: number
  change_percent: number
  volume: number
  bid?: number
  ask?: number
  bid_size?: number
  ask_size?: number
  timestamp: string
}

export interface NewsData {
  title: string
  content: string
  url: string
  source: string
  published_at: string
  sentiment?: number
  symbols?: string[]
  relevance?: number
}

export interface MarketData {
  market_type: string
  total_market_cap: number
  total_volume: number
  dominance: Record<string, number>
  top_gainers: QuoteData[]
  top_losers: QuoteData[]
  timestamp: string
}

export interface SymbolInfo {
  symbol: string
  name: string
  type: string
  exchange: string
  currency?: string
  sector?: string
  industry?: string
}

export interface DataRequest {
  symbol: string
  data_type: 'price' | 'quote' | 'news' | 'financials'
  start_date?: string
  end_date?: string
  params?: Record<string, any>
}

export interface DataResponse<T = any> {
  data: T
  source: string
  cached: boolean
  timestamp: string
}