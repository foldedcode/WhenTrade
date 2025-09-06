import { ref, onUnmounted, getCurrentInstance } from 'vue'
import { websocketService } from '@/services/websocket'

export function useWebSocket() {
  const isConnected = ref(websocketService.isConnected)
  const subscriptions = ref<Map<string, () => void>>(new Map())
  
  const connect = async () => {
    // 直接连接，不需要认证
    await websocketService.connect()
    isConnected.value = websocketService.isConnected
  }
  
  const sendChatMessage = (content: string) => {
    return websocketService.sendChatMessage(content)
  }

  // 添加缺失的方法，委托给websocketService
  const send = (type: string, data?: any) => {
    return websocketService.send({ type, data })
  }

  const subscribe = (messageType: string, handler: (message: any) => void) => {
    const unsubscribe = websocketService.subscribe(messageType, handler)
    const key = `${messageType}-${Math.random()}`
    subscriptions.value.set(key, unsubscribe)
    return unsubscribe
  }

  const unsubscribe = (messageType: string, _params?: any) => {
    // 查找并移除所有匹配的订阅
    const toRemove: string[] = []
    subscriptions.value.forEach((unsubFn, key) => {
      if (key.startsWith(messageType)) {
        unsubFn()
        toRemove.push(key)
      }
    })
    toRemove.forEach(key => subscriptions.value.delete(key))
  }

  // 组件卸载时清理所有订阅
  if (getCurrentInstance()) {
    onUnmounted(() => {
      subscriptions.value.forEach(unsubFn => unsubFn())
      subscriptions.value.clear()
    })
  }
  
  return {
    isConnected,
    connect,
    sendChatMessage,
    send,
    subscribe,
    unsubscribe
  }
}

export function useChatStream(onMessage: (content: string) => void) {
  const isStreaming = ref(false)
  let unsubscribe: (() => void) | null = null
  
  const startStream = () => {
    isStreaming.value = true
    
    // 订阅聊天消息
    unsubscribe = websocketService.subscribe('chat.response', (message) => {
      if (message.data && message.data.content) {
        onMessage(message.data.content)
      }
      
      // 如果消息表示流结束
      if (message.data && message.data.finished) {
        isStreaming.value = false
      }
    })
  }
  
  const stopStream = () => {
    isStreaming.value = false
    if (unsubscribe) {
      unsubscribe()
      unsubscribe = null
    }
  }
  
  // 组件卸载时清理（仅在组件上下文中）
  if (getCurrentInstance()) {
    onUnmounted(() => {
      stopStream()
    })
  }
  
  return {
    isStreaming,
    startStream,
    stopStream
  }
}

export function useWebSocketSubscription() {
  const subscriptions = ref<Map<string, () => void>>(new Map())

  // 订阅特定消息类型
  const subscribe = (messageType: string, params?: any) => {
    const key = `${messageType}-${JSON.stringify(params || {})}`
    
    if (subscriptions.value.has(key)) {
      return // 已经订阅
    }

    // 创建消息处理器
    const handler = (message: any) => {
      // 触发自定义事件供组件监听
      window.dispatchEvent(new CustomEvent(`ws-message:${messageType}`, {
        detail: message.data
      }))
    }

    // 订阅WebSocket消息
    const unsubscribe = websocketService.subscribe(messageType, handler)
    subscriptions.value.set(key, unsubscribe)

    // 发送订阅请求到服务器
    if (messageType === 'agent.thought' && params?.analysisId) {
      websocketService.subscribeAgentThoughts()
    }
  }

  // 取消订阅
  const unsubscribe = (messageType: string, params?: any) => {
    const key = `${messageType}-${JSON.stringify(params || {})}`
    const unsub = subscriptions.value.get(key)
    
    if (unsub) {
      unsub()
      subscriptions.value.delete(key)
    }

    // 发送取消订阅请求到服务器
    if (messageType === 'agent.thought' && params?.analysisId) {
      websocketService.unsubscribeAgentThoughts()
    }
  }

  // 组件卸载时清理所有订阅（仅在组件上下文中）
  if (getCurrentInstance()) {
    onUnmounted(() => {
      subscriptions.value.forEach(unsub => unsub())
      subscriptions.value.clear()
    })
  }

  return {
    subscribe,
    unsubscribe
  }
}