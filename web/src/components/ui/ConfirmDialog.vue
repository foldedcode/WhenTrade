<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click="handleCancel">
        <div class="modal-container bg-neutral-900 rounded-lg shadow-xl border border-neutral-700" @click.stop style="max-width: 400px;">
          <div class="flex items-center justify-between p-4 border-b border-neutral-700">
            <h3 class="text-lg font-bold text-white">{{ title }}</h3>
            <button @click="handleCancel" class="w-8 h-8 flex items-center justify-center rounded hover:bg-neutral-700 transition-colors text-neutral-400 hover:text-white">
              ✕
            </button>
          </div>
          
          <div class="p-6">
            <div class="text-center py-4">
              <div class="text-4xl mb-4">{{ icon }}</div>
              <p class="text-base text-white">
                {{ message }}
              </p>
              <p v-if="description" class="text-sm mt-2 text-neutral-400">
                {{ description }}
              </p>
            </div>
          </div>
          
          <div class="flex justify-end gap-3 p-4 border-t border-neutral-700">
            <button 
              @click="handleCancel" 
              class="px-4 py-2 rounded border border-neutral-600 text-neutral-300 hover:bg-neutral-800 transition-colors"
            >
              {{ cancelText }}
            </button>
            <button 
              @click="handleConfirm" 
              class="px-4 py-2 rounded transition-colors"
              :class="confirmButtonClass"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  visible: boolean
  title?: string
  message: string
  description?: string
  icon?: string
  confirmText?: string
  cancelText?: string
  type?: 'info' | 'warning' | 'danger' | 'success'
}

const props = withDefaults(defineProps<Props>(), {
  title: '确认操作',
  icon: '⚠️',
  confirmText: '确认',
  cancelText: '取消',
  type: 'warning'
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const confirmButtonClass = computed(() => {
  const classes = {
    info: 'bg-blue-500 text-white hover:bg-blue-600',
    warning: 'bg-yellow-500 text-white hover:bg-yellow-600',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    success: 'bg-green-500 text-white hover:bg-green-600'
  }
  return classes[props.type] || 'bg-primary-500 text-white hover:bg-primary-600'
})

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped>

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-enter-active .modal-container,
.fade-leave-active .modal-container {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.fade-enter-from .modal-container {
  transform: scale(0.95) translateY(-10px);
  opacity: 0;
}

.fade-leave-to .modal-container {
  transform: scale(0.95) translateY(-10px);
  opacity: 0;
}
</style>