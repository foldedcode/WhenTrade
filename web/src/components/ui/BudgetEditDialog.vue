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
            <div class="space-y-4">
              <div class="text-center mb-4">
                <div class="terminal-icon text-4xl mb-2">💰</div>
                <p class="text-sm text-neutral-400">{{ label }}</p>
              </div>
              
              <div class="space-y-2">
                <label class="text-xs font-bold tracking-wider uppercase text-neutral-400 block">当前限额</label>
                <div class="text-2xl font-bold text-center text-yellow-400">
                  ${{ currentValue.toFixed(2) }}
                </div>
              </div>
              
              <div class="space-y-2">
                <label class="text-xs font-bold tracking-wider uppercase text-neutral-400 block">新限额</label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-yellow-400 font-bold">$</span>
                  <input
                    ref="inputRef"
                    v-model="newValue"
                    type="text"
                    inputmode="decimal"
                    pattern="[0-9]*\.?[0-9]*"
                    class="w-full pl-8 pr-3 py-2 text-right bg-black/50 border border-neutral-600 rounded text-yellow-400 font-semibold text-xl focus:outline-none focus:border-primary-500 focus:bg-black/70"
                    style="letter-spacing: 0.05em;"
                    placeholder="0.00"
                    @keyup.enter="handleConfirm"
                    @input="handleInput"
                  />
                </div>
              </div>
              
              <div class="p-2 rounded border border-red-500 bg-red-500/10" v-if="errorMessage">
                <span class="text-sm text-red-400">
                  {{ errorMessage }}
                </span>
              </div>
            </div>
          </div>
          
          <div class="flex justify-end gap-3 p-4 border-t border-neutral-700">
            <button 
              @click="handleCancel" 
              class="px-4 py-2 rounded border border-neutral-600 text-neutral-300 hover:bg-neutral-800 transition-colors"
            >
              取消
            </button>
            <button 
              @click="handleConfirm" 
              class="px-4 py-2 rounded bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!isValid"
            >
              确认
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

interface Props {
  visible: boolean
  title: string
  label: string
  currentValue: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  confirm: [value: number]
  cancel: []
}>()

const inputRef = ref<HTMLInputElement>()
const newValue = ref('')
const errorMessage = ref('')

const isValid = computed(() => {
  const num = Number(newValue.value)
  return newValue.value !== '' && !isNaN(num) && num >= 0
})

watch(() => props.visible, (visible) => {
  if (visible) {
    newValue.value = props.currentValue.toString()
    errorMessage.value = ''
    nextTick(() => {
      inputRef.value?.focus()
      inputRef.value?.select()
    })
  }
})

const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  let value = input.value
  
  // 只允许数字和小数点
  value = value.replace(/[^\d.]/g, '')
  
  // 确保只有一个小数点
  const parts = value.split('.')
  if (parts.length > 2) {
    value = parts[0] + '.' + parts.slice(1).join('')
  }
  
  // 限制小数位数为2位
  if (parts.length === 2 && parts[1].length > 2) {
    value = parts[0] + '.' + parts[1].slice(0, 2)
  }
  
  newValue.value = value
}

const handleConfirm = () => {
  if (!isValid.value) {
    errorMessage.value = '请输入有效的金额'
    return
  }
  
  const value = Number(newValue.value)
  if (value < 0) {
    errorMessage.value = '金额不能为负数'
    return
  }
  
  emit('confirm', value)
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

.terminal-icon {
  filter: drop-shadow(0 0 10px rgba(251, 191, 36, 0.5));
}

/* 移除浏览器默认的数字输入控件 */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}
</style>