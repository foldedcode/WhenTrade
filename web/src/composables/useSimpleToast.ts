export interface ToastOptions {
  type?: 'success' | 'error' | 'info' | 'warning'
  title?: string
  message?: string
  duration?: number
}

class ToastManager {
  private static instance: ToastManager
  
  static getInstance(): ToastManager {
    if (!ToastManager.instance) {
      ToastManager.instance = new ToastManager()
    }
    return ToastManager.instance
  }
  
  show(options: ToastOptions | string) {
    const toastOptions: ToastOptions = typeof options === 'string' 
      ? { message: options, type: 'info' } 
      : options
    
    const event = new CustomEvent('show-toast', {
      detail: {
        type: toastOptions.type || 'info',
        title: toastOptions.title,
        message: toastOptions.message,
        duration: toastOptions.duration || 3000
      }
    })
    
    window.dispatchEvent(event)
  }
  
  success(message: string, title?: string) {
    this.show({ type: 'success', message, title })
  }
  
  error(message: string, title?: string) {
    this.show({ type: 'error', message, title })
  }
  
  info(message: string, title?: string) {
    this.show({ type: 'info', message, title })
  }
  
  warning(message: string, title?: string) {
    this.show({ type: 'warning', message, title })
  }
}

export function useSimpleToast() {
  const toast = ToastManager.getInstance()
  
  return {
    toast,
    showToast: toast.show.bind(toast),
    showSuccess: toast.success.bind(toast),
    showError: toast.error.bind(toast),
    showInfo: toast.info.bind(toast),
    showWarning: toast.warning.bind(toast)
  }
}

// 导出全局实例便于直接使用
export const simpleToast = ToastManager.getInstance()