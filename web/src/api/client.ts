/**
 * 统一的API客户端
 * 提供标准化的HTTP请求处理、认证、错误处理等功能
 */

// import { useToast } from '@/composables/useToast'

export interface RequestConfig {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  params?: Record<string, any>
  data?: any
  headers?: Record<string, string>
  timeout?: number
}

export interface ApiResponse<T = any> {
  data: T
  status: number
  message?: string
}

export class ApiError extends Error {
  constructor(
    public code: string,
    public message: string,
    public status?: number,
    public details?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export enum ErrorCode {
  NETWORK_ERROR = 'NETWORK_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  SERVER_ERROR = 'SERVER_ERROR',
  TASK_FAILED = 'TASK_FAILED'
}

class ApiClient {
  private baseURL: string
  private timeout: number
  private maxRetries: number = 3
  private retryDelay: number = 1000

  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    this.timeout = parseInt(import.meta.env.VITE_API_TIMEOUT || '10000')
  }

  /**
   * 发送HTTP请求
   */
  async request<T = any>(config: RequestConfig): Promise<T> {
    // 构建请求URL
    const url = config.url.startsWith('http') 
      ? config.url 
      : `${this.baseURL}${config.url}`

    // 构建查询参数
    const queryString = config.params 
      ? '?' + new URLSearchParams(config.params).toString()
      : ''

    // 构建请求头
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...config.headers
    }

    // 简化版本无需认证

    // 配置请求选项
    const requestOptions: RequestInit = {
      method: config.method || 'GET',
      headers,
      signal: AbortSignal.timeout(config.timeout || this.timeout)
    }

    // 添加请求体
    if (config.data && ['POST', 'PUT', 'PATCH'].includes(requestOptions.method!)) {
      requestOptions.body = JSON.stringify(config.data)
    }

    // 执行请求（带重试）
    let lastError: any
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const response = await fetch(url + queryString, requestOptions)
        
        // 处理响应
        if (!response.ok) {
          await this.handleErrorResponse(response)
        }

        // 解析响应
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          return await response.json()
        } else {
          return await response.text() as any
        }
      } catch (error: any) {
        lastError = error
        
        // 如果是客户端错误，不重试
        if (error instanceof ApiError && 
            [ErrorCode.VALIDATION_ERROR].includes(error.code as ErrorCode)) {
          throw error
        }

        // 如果不是最后一次尝试，等待后重试
        if (attempt < this.maxRetries - 1) {
          await this.delay(this.retryDelay * (attempt + 1))
          continue
        }
      }
    }

    // 所有重试都失败
    throw this.normalizeError(lastError)
  }

  /**
   * 处理错误响应
   */
  private async handleErrorResponse(response: Response): Promise<never> {
    let errorData: any = {}
    
    try {
      const contentType = response.headers.get('content-type')
      if (contentType?.includes('application/json')) {
        errorData = await response.json()
      } else {
        errorData = { message: await response.text() }
      }
    } catch {
      errorData = { message: 'Unknown error occurred' }
    }

    // 根据状态码确定错误类型
    let errorCode: ErrorCode
    switch (response.status) {
      case 404:
        errorCode = ErrorCode.NOT_FOUND
        break
      case 422:
      case 400:
        errorCode = ErrorCode.VALIDATION_ERROR
        break
      default:
        errorCode = response.status >= 500 
          ? ErrorCode.SERVER_ERROR 
          : ErrorCode.NETWORK_ERROR
    }

    throw new ApiError(
      errorCode,
      errorData.detail || errorData.message || 'Request failed',
      response.status,
      errorData
    )
  }

  /**
   * 标准化错误
   */
  private normalizeError(error: any): ApiError {
    if (error instanceof ApiError) {
      return error
    }

    if (error.name === 'AbortError') {
      return new ApiError(
        ErrorCode.NETWORK_ERROR,
        'Request timeout',
        0,
        { timeout: true }
      )
    }

    return new ApiError(
      ErrorCode.NETWORK_ERROR,
      error.message || 'Network error occurred',
      0,
      error
    )
  }


  /**
   * 延迟函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * GET请求快捷方法
   */
  async get<T = any>(url: string, params?: Record<string, any>, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({
      ...config,
      url,
      method: 'GET',
      params
    })
  }

  /**
   * POST请求快捷方法
   */
  async post<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({
      ...config,
      url,
      method: 'POST',
      data
    })
  }

  /**
   * PUT请求快捷方法
   */
  async put<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({
      ...config,
      url,
      method: 'PUT',
      data
    })
  }

  /**
   * DELETE请求快捷方法
   */
  async delete<T = any>(url: string, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({
      ...config,
      url,
      method: 'DELETE'
    })
  }

  /**
   * PATCH请求快捷方法
   */
  async patch<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({
      ...config,
      url,
      method: 'PATCH',
      data
    })
  }
}

// 导出单例
export const apiClient = new ApiClient()

// 导出便捷方法
export const api = {
  get: apiClient.get.bind(apiClient),
  post: apiClient.post.bind(apiClient),
  put: apiClient.put.bind(apiClient),
  delete: apiClient.delete.bind(apiClient),
  patch: apiClient.patch.bind(apiClient),
  request: apiClient.request.bind(apiClient)
}