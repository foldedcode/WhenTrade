/**
 * HTTP 请求工具
 * 基于 fetch API 的封装
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

interface RequestOptions extends RequestInit {
  params?: Record<string, any>
  timeout?: number
}

class HttpClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private async request<T>(url: string, options: RequestOptions = {}): Promise<T> {
    const { params, timeout, ...fetchOptions } = options

    // 处理查询参数
    if (params) {
      const queryString = new URLSearchParams(params).toString()
      url = `${url}${queryString ? `?${queryString}` : ''}`
    }

    // 设置默认 headers
    const headers = {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    }

    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    try {
      const controller = new AbortController()
      let timeoutId: number | undefined

      if (timeout) {
        timeoutId = window.setTimeout(() => controller.abort(), timeout)
      }

      const response = await fetch(`${this.baseURL}${url}`, {
        ...fetchOptions,
        headers,
        signal: controller.signal,
      })

      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`
        try {
          const error = await response.json()
          errorMessage = error.detail || error.message || errorMessage
        } catch {
          // 无法解析错误响应为JSON
        }
        throw new Error(errorMessage)
      }

      // 处理空响应
      if (response.status === 204) {
        return {} as T
      }

      return await response.json()
    } catch (error) {
      console.error('Request failed:', {
        url: `${this.baseURL}${url}`,
        method: fetchOptions.method || 'GET',
        error
      })
      throw error
    }
  }

  get<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET' })
  }

  post<T>(url: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  put<T>(url: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  delete<T>(url: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'DELETE' })
  }

  patch<T>(url: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }
}

// 创建默认实例
const httpClient = new HttpClient(API_BASE_URL)

// 导出便捷方法
export const request = {
  get: <T>(url: string, options?: RequestOptions) => httpClient.get<T>(url, options),
  post: <T>(url: string, data?: any, options?: RequestOptions) => httpClient.post<T>(url, data, options),
  put: <T>(url: string, data?: any, options?: RequestOptions) => httpClient.put<T>(url, data, options),
  delete: <T>(url: string, options?: RequestOptions) => httpClient.delete<T>(url, options),
  patch: <T>(url: string, data?: any, options?: RequestOptions) => httpClient.patch<T>(url, data, options),
}

export default httpClient