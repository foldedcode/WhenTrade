<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast-item"
        :class="[`toast--${toast.type}`, { 'toast--closing': toast.closing }]"
        @click="removeToast(toast.id)"
      >
        <div class="toast-icon">{{ getIcon(toast.type) }}</div>
        <div class="toast-content">
          <div class="text-sm font-semibold text-white">
            {{ toast.title || getDefaultTitle(toast.type) }}
          </div>
          <div v-if="toast.message" class="text-xs text-neutral-300 mt-1">
            {{ toast.message }}
          </div>
        </div>
        <div class="toast-progress" :style="{ animationDuration: `${toast.duration}ms` }"></div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

export interface Toast {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  title?: string
  message?: string
  duration: number
  closing?: boolean
}

const toasts = ref<Toast[]>([])
const timers = new Map<string, NodeJS.Timeout>()

const getIcon = (type: Toast['type']) => {
  const icons = {
    success: '✅',
    error: '❌',
    info: 'ℹ️',
    warning: '⚠️'
  }
  return icons[type]
}

const getDefaultTitle = (type: Toast['type']) => {
  const titles = {
    success: '成功',
    error: '错误',
    info: '提示',
    warning: '警告'
  }
  return titles[type]
}

const addToast = (toast: Omit<Toast, 'id'>) => {
  const id = Date.now().toString()
  const newToast: Toast = {
    ...toast,
    id,
    duration: toast.duration || 3000
  }
  
  toasts.value.push(newToast)
  
  // 设置自动移除定时器
  const timer = setTimeout(() => {
    removeToast(id)
  }, newToast.duration)
  
  timers.set(id, timer)
}

const removeToast = (id: string) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    // 添加关闭动画类
    toasts.value[index].closing = true
    
    // 等待动画完成后移除
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
      const timer = timers.get(id)
      if (timer) {
        clearTimeout(timer)
        timers.delete(id)
      }
    }, 300)
  }
}

// 暴露方法供外部调用
defineExpose({
  addToast
})

// 监听自定义事件
const handleToastEvent = (event: CustomEvent) => {
  addToast(event.detail)
}

onMounted(() => {
  window.addEventListener('show-toast', handleToastEvent as EventListener)
})

onUnmounted(() => {
  window.removeEventListener('show-toast', handleToastEvent as EventListener)
  // 清理所有定时器
  timers.forEach(timer => clearTimeout(timer))
  timers.clear()
})
</script>

<style scoped>

.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  pointer-events: none;
}

.toast-item {
  @apply flex items-start space-x-3 p-4 rounded-lg shadow-lg cursor-pointer mb-3;
  min-width: 300px;
  max-width: 500px;
  background: rgba(31, 31, 31, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-left: 4px solid;
  position: relative;
  overflow: hidden;
  pointer-events: all;
  transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
}

.toast-item:hover {
  transform: translateX(-4px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
}

/* 类型样式 */
.toast--success {
  border-left-color: #10b981;
}

.toast--success .toast-icon {
  color: #10b981;
}

.toast--error {
  border-left-color: #ef4444;
}

.toast--error .toast-icon {
  color: #ef4444;
}

.toast--info {
  border-left-color: #3b82f6;
}

.toast--info .toast-icon {
  color: #3b82f6;
}

.toast--warning {
  border-left-color: #f59e0b;
}

.toast--warning .toast-icon {
  color: #f59e0b;
}

/* 图标样式 */
.toast-icon {
  font-size: 1.5rem;
  filter: drop-shadow(0 0 8px currentColor);
}

/* 内容样式 */
.toast-content {
  flex: 1;
}

/* 进度条 */
.toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: currentColor;
  opacity: 0.3;
  animation: toast-progress linear forwards;
}

@keyframes toast-progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

/* 动画 */
.toast-enter-active {
  animation: toast-slide-in 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-leave-active {
  animation: toast-slide-out 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes toast-slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes toast-slide-out {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

.toast--closing {
  transform: translateX(100%);
  opacity: 0;
}

/* 响应式 */
@media (max-width: 640px) {
  .toast-container {
    top: 10px;
    right: 10px;
    left: 10px;
  }
  
  .toast-item {
    min-width: auto;
    max-width: 100%;
  }
}
</style>