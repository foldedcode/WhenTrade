/**
 * 防抖函数 - 延迟执行直到停止触发一段时间后
 * @param func 要防抖的函数
 * @param delay 延迟时间（毫秒）
 * @returns 防抖后的函数，带有cancel方法
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): {
  (...args: Parameters<T>): void
  cancel: () => void
} {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  
  const debounced = function (this: any, ...args: Parameters<T>) {
    // 清除之前的定时器
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }
    
    // 设置新的定时器
    timeoutId = setTimeout(() => {
      func.apply(this, args)
      timeoutId = null
    }, delay)
  }
  
  // 添加取消方法
  debounced.cancel = () => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }
  
  return debounced
}

/**
 * 节流函数 - 限制函数在指定时间内只能执行一次
 * @param func 要节流的函数
 * @param limit 时间限制（毫秒）
 * @returns 节流后的函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  
  return function (this: any, ...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}