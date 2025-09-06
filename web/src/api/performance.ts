/**
 * 性能监控API客户端
 */

import { apiClient } from './client'

// 性能健康检查响应类型
export interface HealthCheckResponse {
  timestamp: string
  overall_status: string
  components: {
    system: {
      status: string
      platform?: string
      python_version?: string
      architecture?: string
    }
    api: {
      status: string
      message: string
      process_id?: number
    }
    database?: {
      status: string
      message: string
    }
    cache?: {
      status: string
      message: string
    }
  }
  error?: string
}

// 性能摘要响应类型
export interface PerformanceSummaryResponse {
  status: string
  data: {
    timestamp: string
    system_performance: {
      platform: string
      python_version: string
      process_id: number
      uptime_info: string
    }
    api_performance: {
      status: string
      message: string
      endpoints_status: string
    }
    database_performance: {
      status: string
      message: string
    }
    cache_performance: {
      status: string
      message: string
    }
  }
  note?: string
  error?: string
}

class PerformanceAPI {
  /**
   * 测试API连接
   */
  async test(): Promise<any> {
    const response = await apiClient.get('/performance/test')
    return response.data
  }

  /**
   * 获取健康检查状态
   */
  async getHealthCheck(): Promise<HealthCheckResponse> {
    const response = await apiClient.get('/performance/health')
    return response.data
  }

  /**
   * 获取性能摘要
   */
  async getPerformanceSummary(): Promise<PerformanceSummaryResponse> {
    const response = await apiClient.get('/performance/metrics/summary')
    return response.data
  }

  /**
   * 获取详细性能指标（需要管理员权限）
   */
  async getDetailedMetrics(): Promise<any> {
    try {
      const response = await apiClient.get('/performance/metrics/detailed')
      return response.data
    } catch (error) {
      console.warn('获取详细性能指标失败，可能需要管理员权限:', error)
      throw error
    }
  }

  /**
   * 获取数据库统计（需要管理员权限）
   */
  async getDatabaseStats(): Promise<any> {
    try {
      const response = await apiClient.get('/performance/database/stats')
      return response.data
    } catch (error) {
      console.warn('获取数据库统计失败，可能需要管理员权限:', error)
      throw error
    }
  }

  /**
   * 获取任务队列统计（需要管理员权限）
   */
  async getTaskStats(): Promise<any> {
    try {
      const response = await apiClient.get('/performance/tasks/stats')
      return response.data
    } catch (error) {
      console.warn('获取任务队列统计失败，可能需要管理员权限:', error)
      throw error
    }
  }

  /**
   * 获取优化建议（需要管理员权限）
   */
  async getOptimizationRecommendations(): Promise<any> {
    try {
      const response = await apiClient.get('/performance/recommendations')
      return response.data
    } catch (error) {
      console.warn('获取优化建议失败，可能需要管理员权限:', error)
      throw error
    }
  }

  /**
   * 提交测试任务（需要管理员权限）
   */
  async submitTestTask(options: {
    task_name?: string
    priority?: 'low' | 'normal' | 'high' | 'critical'
    cpu_bound?: boolean
  } = {}): Promise<any> {
    try {
      const response = await apiClient.post('/performance/tasks/test', {
        task_name: options.task_name || 'frontend_test',
        priority: options.priority || 'normal',
        cpu_bound: options.cpu_bound || false
      })
      return response.data
    } catch (error) {
      console.warn('提交测试任务失败，可能需要管理员权限:', error)
      throw error
    }
  }
}

// 创建并导出实例
export const performanceApi = new PerformanceAPI()

// 类型已在上方导出