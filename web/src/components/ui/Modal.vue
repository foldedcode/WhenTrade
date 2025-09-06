<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isVisible"
        class="modal-overlay"
        @click="handleOverlayClick"
      >
        <transition
          enter-active-class="transition-all duration-200"
          leave-active-class="transition-all duration-200"
          enter-from-class="opacity-0 scale-95"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="isVisible"
            class="modal-container"
            :style="{ width: width || 'auto', maxWidth: maxWidth || '90vw' }"
            @click.stop
          >
            <!-- Modal Header -->
            <div class="modal-header">
              <h2 class="modal-title">{{ title }}</h2>
              <button
                v-if="closable"
                class="modal-close"
                @click="handleClose"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Modal Body -->
            <div class="modal-body">
              <slot></slot>
            </div>

            <!-- Modal Footer -->
            <div v-if="$slots.footer" class="modal-footer">
              <slot name="footer"></slot>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'

interface Props {
  visible?: boolean
  modelValue?: boolean
  title?: string
  width?: string
  maxWidth?: string
  closeOnOverlay?: boolean
  closable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  closeOnOverlay: true,
  closable: true
})

const emit = defineEmits<{
  close: []
  'update:modelValue': [value: boolean]
}>()

// 计算实际的可见状态
const isVisible = computed(() => {
  return props.modelValue !== undefined ? props.modelValue : props.visible
})

// 处理关闭事件
function handleClose() {
  emit('close')
  if (props.modelValue !== undefined) {
    emit('update:modelValue', false)
  }
}

// 处理遮罩层点击
function handleOverlayClick() {
  if (props.closeOnOverlay && props.closable) {
    handleClose()
  }
}

// 处理 ESC 键
function handleEscKey(event: KeyboardEvent) {
  if (event.key === 'Escape' && isVisible.value && props.closable) {
    handleClose()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscKey)
  if (isVisible.value) {
    document.body.style.overflow = 'hidden'
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscKey)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* 遮罩层 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--od-spacing-xl);
}

/* 模态框容器 */
.modal-container {
  background: var(--od-surface);
  border-radius: var(--od-radius-lg);
  box-shadow: var(--od-shadow-xl);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* 模态框头部 */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--od-spacing-lg) var(--od-spacing-xl);
  border-bottom: 1px solid var(--od-border);
}

.modal-title {
  margin: 0;
  font-size: var(--od-font-xl);
  font-weight: 600;
  color: var(--od-text-primary);
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--od-radius-md);
  color: var(--od-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.modal-close:hover {
  background: var(--od-background-light);
  color: var(--od-text-primary);
}

/* 模态框主体 */
.modal-body {
  flex: 1;
  padding: var(--od-spacing-xl);
  overflow-y: auto;
  max-height: calc(85vh - 140px);
}

/* 模态框底部 */
.modal-footer {
  padding: var(--od-spacing-lg) var(--od-spacing-xl);
  border-top: 1px solid var(--od-border);
}

/* 响应式 */
@media (max-width: 640px) {
  .modal-overlay {
    padding: 0;
  }
  
  .modal-container {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    border-radius: 0;
  }
  
  .modal-body {
    max-height: calc(100vh - 140px);
  }
}
</style>