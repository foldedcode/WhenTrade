// 错误级别枚举
export enum ErrorLevel {
  INFO = 'info',
  WARNING = 'warning', 
  ERROR = 'error',
  CRITICAL = 'critical'
}

// 错误类型枚举
export enum ErrorType {
  NETWORK = 'network',
  API = 'api',
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  BUSINESS = 'business',
  SYSTEM = 'system',
  UNKNOWN = 'unknown'
}

// 错误显示策略
export enum ErrorDisplayStrategy {
  TOAST = 'toast',
  MODAL = 'modal',
  INLINE = 'inline',
  CONSOLE = 'console',
  SILENT = 'silent'
}

// 基础错误接口
export interface BaseError {
  id: string
  code: string
  type: ErrorType
  level: ErrorLevel
  message: string
  description?: string
  timestamp: Date
  context?: Record<string, any>
  stack?: string
  displayStrategy: ErrorDisplayStrategy
}

// API错误接口
export interface ApiError extends BaseError {
  status: number
  statusText: string
  url: string
  method: string
  requestData?: any
  responseData?: any
}

// 网络错误接口
export interface NetworkError extends BaseError {
  isTimeout: boolean
  isOffline: boolean
  retryCount: number
  maxRetries: number
}

// 验证错误接口
export interface ValidationError extends BaseError {
  field: string
  value: any
  rule: string
  constraints: Record<string, any>
}

// 业务错误接口
export interface BusinessError extends BaseError {
  businessCode: string
  category: string
  actionRequired?: string
}

// 错误处理选项
export interface ErrorHandleOptions {
  showToast?: boolean
  showModal?: boolean
  logToConsole?: boolean
  logToStorage?: boolean
  autoRetry?: boolean
  maxRetries?: number
  retryDelay?: number
  onRetry?: () => void
  onError?: (error: BaseError) => void
}

// 错误恢复策略
export interface ErrorRecoveryStrategy {
  canRecover: boolean
  recoveryAction?: () => Promise<void>
  recoveryMessage?: string
  fallbackData?: any
}

// Toast 通知选项
export interface ToastOptions {
  id?: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  duration?: number
  persistent?: boolean
  actions?: ToastAction[]
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
}

// Toast 操作
export interface ToastAction {
  label: string
  action: () => void
  style?: 'primary' | 'secondary' | 'danger'
}

// Modal 对话框选项
export interface ModalOptions {
  id?: string
  type: 'info' | 'warning' | 'error' | 'confirm'
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  persistent?: boolean
  onConfirm?: () => void | Promise<void>
  onCancel?: () => void
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

// 错误统计信息
export interface ErrorStats {
  totalErrors: number
  errorsByType: Record<ErrorType, number>
  errorsByLevel: Record<ErrorLevel, number>
  recentErrors: BaseError[]
  errorRate: number
  lastErrorTime?: Date
}

// 错误处理上下文
export interface ErrorContext {
  userId?: string
  sessionId: string
  page: string
  action: string
  userAgent: string
  timestamp: Date
  additionalData?: Record<string, any>
} 