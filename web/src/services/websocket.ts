/**
 * WebSocket客户端服务
 * 处理与后端的实时通信
 */

// 认证功能已移除，等待 Web3Auth 集成

export interface WebSocketMessage {
  type: string
  id?: string
  data?: any
  error?: string
  timestamp?: string
  // LLM元数据支持（可选字段，保持向后兼容）
  llmProvider?: string
  llmModel?: string  
  llmBackend?: string
}

export type MessageHandler = (message: WebSocketMessage) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectInterval: number = 5000
  private reconnectTimer: NodeJS.Timeout | null = null
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map()
  private pendingMessages: WebSocketMessage[] = []
  private isConnecting: boolean = false
  private connectionId: string | null = null
  private connectionPromise: Promise<void> | undefined = undefined

  constructor() {
    // 构建WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_BASE_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
    this.url = `${protocol}//${host}/api/v1/ws`
  }

  /**
   * 连接到WebSocket服务器
   */
  async connect(token?: string): Promise<void> {
    // 如果已连接，直接返回
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }
    
    // 如果正在连接，返回现有的连接Promise
    if (this.isConnecting && this.connectionPromise) {
      return this.connectionPromise
    }

    this.isConnecting = true

    // 创建连接Promise
    this.connectionPromise = new Promise<void>((resolve, reject) => {
      try {
        // 构建带认证的WebSocket URL
        let wsUrl = this.url
        if (token) {
          wsUrl += `?token=${encodeURIComponent(token)}`
        }
        
        this.ws = new WebSocket(wsUrl)

        // 设置连接超时
        const connectionTimeout = setTimeout(() => {
          if (this.ws?.readyState !== WebSocket.OPEN) {
            this.ws?.close()
            this.isConnecting = false
            this.connectionPromise = undefined
            reject(new Error('WebSocket connection timeout'))
          }
        }, 10000) // 10秒超时

        this.ws.onopen = () => {
          // console.log('WebSocket connected')
          clearTimeout(connectionTimeout)
          this.isConnecting = false
          this.connectionPromise = undefined
          this.clearReconnectTimer()
          
          // 发送所有待发送的消息
          while (this.pendingMessages.length > 0) {
            const message = this.pendingMessages.shift()
            if (message) {
              this.send(message)
            }
          }
          
          resolve()
        }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          clearTimeout(connectionTimeout)
          this.isConnecting = false
          this.connectionPromise = undefined
          reject(error)
        }

        this.ws.onclose = (event) => {
          // console.log('WebSocket closed:', event.code, event.reason)
          clearTimeout(connectionTimeout)
          this.isConnecting = false
          this.connectionPromise = undefined
          this.connectionId = null
        
        // 处理认证错误
        if (event.code === 4001) {
          console.error('WebSocket authentication failed: Missing token')
          this.handleAuthError('Missing authentication token')
          return
        } else if (event.code === 4002) {
          console.error('WebSocket authentication failed: Invalid token')
          this.handleAuthError('Invalid or expired token')
          return
        }
        
        // 尝试重连
        if (event.code !== 1000) { // 非正常关闭
          this.scheduleReconnect()
        }
      }
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        this.isConnecting = false
        this.connectionPromise = undefined
        reject(error)
      }
    })
    
    return this.connectionPromise
  }

  /**
   * 使用认证Token连接
   */
  async connectWithAuth(token: string): Promise<void> {
    return this.connect(token)
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(): void {
    this.clearReconnectTimer()
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.connectionId = null
  }

  /**
   * 发送消息
   */
  send(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // 连接未建立，将消息加入待发送队列
      this.pendingMessages.push(message)
      // 需要从store获取token再连接
      console.warn('WebSocket未连接，需要先通过connectWithAuth方法建立连接')
    }
  }

  /**
   * 订阅消息类型
   */
  subscribe(type: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set())
    }
    
    this.messageHandlers.get(type)!.add(handler)
    
    // 返回取消订阅函数
    return () => {
      const handlers = this.messageHandlers.get(type)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          this.messageHandlers.delete(type)
        }
      }
    }
  }

  /**
   * 订阅主题
   */
  subscribeTopic(topic: string): void {
    this.send({
      type: 'subscribe',
      topic,
      id: `sub-${Date.now()}`
    })
  }

  /**
   * 取消订阅主题
   */
  unsubscribeTopic(topic: string): void {
    this.send({
      type: 'unsubscribe',
      topic,
      id: `unsub-${Date.now()}`
    })
  }

  /**
   * 发送ping消息
   */
  ping(): void {
    this.send({
      type: 'ping',
      id: `ping-${Date.now()}`
    })
  }

  /**
   * 执行工具
   */
  executeTool(tool: string, context: any): string {
    const id = `tool-${Date.now()}`
    this.send({
      type: 'tool.execute',
      id,
      data: {
        tool,
        context
      }
    })
    return id
  }

  /**
   * 订阅分析任务的更新
   * @param analysisId 要订阅的分析任务ID
   * @param analysisParams 完整的分析参数（符合Linus原则：数据直接流向需要的地方）
   */
  subscribeToAnalysis(analysisId: string, analysisParams?: any): void {
    if (!analysisId) {
      console.error('❌ subscribeToAnalysis: analysisId不能为空')
      return
    }
    
    const id = `subscribe-${Date.now()}`
    const message = {
      type: 'analysis.subscribe',
      id,
      data: {
        analysisId,
        // 如果提供了分析参数，则一并发送（消除后端数据库查询的需要）
        ...(analysisParams || {})
      }
    }
    
    // console.log(`📡 订阅分析任务 ${analysisId} 的更新, 消息ID: ${id}`)
    
    try {
      this.send(message)
      // console.log(`✅ 订阅消息已发送:`, message)
    } catch (error) {
      console.error(`❌ 发送订阅消息失败:`, error)
    }
  }

  /**
   * 取消分析
   */
  cancelAnalysis(taskId: string): void {
    this.send({
      type: 'analysis.cancel',
      id: `cancel-${Date.now()}`,
      data: {
        taskId
      }
    })
  }

  /**
   * 订阅agent思考流
   */
  subscribeAgentThoughts(agentId?: string): void {
    this.send({
      type: 'agent.thought.subscribe',
      id: `thought-sub-${Date.now()}`,
      data: {
        agentId // 如果为空，订阅所有agent的思考
      }
    })
  }

  /**
   * 取消订阅agent思考流
   */
  unsubscribeAgentThoughts(agentId?: string): void {
    this.send({
      type: 'agent.thought.unsubscribe',
      id: `thought-unsub-${Date.now()}`,
      data: {
        agentId
      }
    })
  }

  /**
   * 发送聊天消息
   */
  sendChatMessage(content: string): string {
    const id = `chat-${Date.now()}`
    this.send({
      type: 'chat.message',
      id,
      data: {
        content
      }
    })
    return id
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取连接ID
   */
  get getConnectionId(): string | null {
    return this.connectionId
  }

  /**
   * 测试连接
   */
  async testConnection(token?: string): Promise<{ success: boolean; message: string }> {
    return new Promise((resolve) => {
      // 设置超时
      const timeout = setTimeout(() => {
        resolve({
          success: false,
          message: 'Connection timeout'
        })
      }, 5000)

      // 监听连接事件
      const unsubscribe = this.subscribe('connection', (message) => {
        clearTimeout(timeout)
        unsubscribe()
        resolve({
          success: true,
          message: 'Connection established successfully'
        })
      })

      // 监听认证错误
      const unsubscribeError = this.subscribe('auth_error', (message) => {
        clearTimeout(timeout)
        unsubscribe()
        unsubscribeError()
        resolve({
          success: false,
          message: message.error || 'Authentication failed'
        })
      })

      // 尝试连接
      this.connect(token)
    })
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    // 处理压缩消息
    if ((message as any).compressed) {
      message = this.decompressMessage(message)
    }
    
    // 处理思考流批次
    if (message.type === 'thought_batch' || message.type === 'thought_batch_compressed') {
      this.handleThoughtBatch(message)
      return
    }
    
    // 处理连接消息
    if (message.type === 'connection' && message.data?.connectionId) {
      this.connectionId = message.data.connectionId
    }

    // 分发消息给订阅者
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          console.error('Error in message handler:', error)
        }
      })
    }

    // 通用消息处理器
    const allHandlers = this.messageHandlers.get('*')
    if (allHandlers) {
      allHandlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          console.error('Error in wildcard handler:', error)
        }
      })
    }
  }
  
  /**
   * 解压消息
   */
  private decompressMessage(message: any): WebSocketMessage {
    // 简单实现，实际应该使用pako或其他压缩库
    if (message.encoding === 'gzip') {
      // console.log('收到压缩消息，压缩率:', 
      //   Math.round((1 - message.compressed_size / message.original_size) * 100) + '%')
      // 这里应该解压数据，但浏览器端需要引入压缩库
      // 暂时返回原消息结构
      return {
        type: message.type || 'compressed',
        data: message
      }
    }
    return message
  }
  
  /**
   * 处理思考流批次
   */
  private handleThoughtBatch(batch: any): void {
    const thoughts = batch.thoughts || []
    const analysisId = batch.analysis_id
    
    // 将批次中的每个思考分发给订阅者
    thoughts.forEach((thought: any) => {
      const thoughtMessage: WebSocketMessage = {
        type: 'agent.thought',
        data: {
          ...thought,
          analysisId
        }
      }
      
      // 分发给思考流订阅者
      const handlers = this.messageHandlers.get('agent.thought')
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(thoughtMessage)
          } catch (error) {
            console.error('Error in thought handler:', error)
          }
        })
      }
    })
    
    // 发送批次统计信息
    const statsMessage: WebSocketMessage = {
      type: 'thought.batch.stats',
      data: {
        analysisId,
        count: batch.count,
        timestamp: batch.timestamp
      }
    }
    
    const statsHandlers = this.messageHandlers.get('thought.batch.stats')
    if (statsHandlers) {
      statsHandlers.forEach(handler => {
        try {
          handler(statsMessage)
        } catch (error) {
          console.error('Error in stats handler:', error)
        }
      })
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return
    }

    // console.log(`Scheduling reconnect in ${this.reconnectInterval}ms`)
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, this.reconnectInterval)
  }

  /**
   * 清除重连定时器
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * 处理认证错误
   */
  private handleAuthError(reason: string): void {
    // 触发认证失败事件
    const handlers = this.messageHandlers.get('auth_error')
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler({
            type: 'auth_error',
            error: reason,
            timestamp: new Date().toISOString()
          })
        } catch (error) {
          console.error('Error in auth error handler:', error)
        }
      })
    }

    // 认证功能已移除
    console.warn('Authentication error:', reason)
  }
}

// 创建单例实例
export const websocketService = new WebSocketService()

// Vue插件
export default {
  install(app: any) {
    app.config.globalProperties.$ws = websocketService
    app.provide('websocket', websocketService)
  }
}