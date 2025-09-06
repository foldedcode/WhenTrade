import { ref, reactive, computed } from 'vue'
import { ToastOptions, ToastAction } from '../types/error'

// 单个Toast项的扩展接口
interface ToastItem extends ToastOptions {
  id: string
  createdAt: Date
  isVisible: boolean
}

// 全局Toast状态
const toastState = reactive({
  toasts: [] as ToastItem[],
  maxToasts: 5,
  defaultDuration: 5000,
  defaultPosition: 'top-right' as ToastOptions['position']
})

export const useToast = () => {
  // 生成唯一ID
  const generateId = (): string => {
    return `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // 显示Toast
  const show = (options: ToastOptions): string => {
    const id = options.id || generateId()
    
    const toast: ToastItem = {
      id,
      type: options.type,
      title: options.title,
      message: options.message,
      duration: options.duration ?? toastState.defaultDuration,
      persistent: options.persistent ?? false,
      actions: options.actions,
      position: options.position ?? toastState.defaultPosition,
      createdAt: new Date(),
      isVisible: true
    }

    // 添加到开头
    toastState.toasts.unshift(toast)

    // 限制最大数量
    if (toastState.toasts.length > toastState.maxToasts) {
      const removedToast = toastState.toasts.pop()
      if (removedToast) {
        removedToast.isVisible = false
      }
    }

    // 自动移除（如果不是持久化的）
    if (!toast.persistent && toast.duration && toast.duration > 0) {
      setTimeout(() => {
        hide(id)
      }, toast.duration)
    }

    return id
  }

  // 隐藏Toast
  const hide = (id: string) => {
    const toast = toastState.toasts.find(t => t.id === id)
    if (toast) {
      toast.isVisible = false
      // 延迟移除，给动画时间
      setTimeout(() => {
        const index = toastState.toasts.findIndex(t => t.id === id)
        if (index > -1) {
          toastState.toasts.splice(index, 1)
        }
      }, 300)
    }
  }

  // 清除所有Toast
  const clear = () => {
    toastState.toasts.forEach(toast => {
      toast.isVisible = false
    })
    setTimeout(() => {
      toastState.toasts.length = 0
    }, 300)
  }

  // 便捷方法
  const success = (title: string, message?: string, options?: Partial<ToastOptions>) => {
    return show({
      type: 'success',
      title,
      message,
      ...options
    })
  }

  const error = (title: string, message?: string, options?: Partial<ToastOptions>) => {
    return show({
      type: 'error',
      title,
      message,
      persistent: true, // 错误默认持久化显示
      ...options
    })
  }

  const warning = (title: string, message?: string, options?: Partial<ToastOptions>) => {
    return show({
      type: 'warning',
      title,
      message,
      ...options
    })
  }

  const info = (title: string, message?: string, options?: Partial<ToastOptions>) => {
    return show({
      type: 'info',
      title,
      message,
      ...options
    })
  }

  // 计算属性
  const visibleToasts = computed(() => 
    toastState.toasts.filter(toast => toast.isVisible)
  )

  const toastCount = computed(() => toastState.toasts.length)

  const hasToasts = computed(() => toastState.toasts.length > 0)

  const toastsByPosition = computed(() => {
    const positions: Record<string, ToastItem[]> = {}
    
    toastState.toasts.forEach(toast => {
      const position = toast.position || 'top-right'
      if (!positions[position]) {
        positions[position] = []
      }
      positions[position].push(toast)
    })
    
    return positions
  })

  return {
    // 状态
    toasts: toastState.toasts,
    visibleToasts,
    toastCount,
    hasToasts,
    toastsByPosition,

    // 方法
    show,
    hide,
    clear,

    // 便捷方法
    success,
    error,
    warning,
    info
  }
} 