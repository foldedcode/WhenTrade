<template>
  <div class="time-selector--professional">
    <label class="block text-sm font-medium mb-2" style="color: var(--ft-text-secondary)">
      {{ t('common.timeRange.label') }}
    </label>
    
    <div class="space-y-2" :class="{ 'time-selector--disabled': disabled }">
      <!-- 预设时间按钮 -->
      <div class="grid grid-cols-5 gap-1">
        <button
          v-for="preset in timePresets"
          :key="preset.value"
          @click="selectPreset(preset.value)"
          :disabled="disabled"
          :class="[
            'btn--professional--compact text-xs py-1.5 px-2 min-w-0',
            selectedPreset === preset.value ? 'btn--primary' : 'btn--secondary'
          ]"
        >
          <span class="block truncate" :title="preset.label">{{ preset.label }}</span>
        </button>
      </div>
      
      <!-- 自定义时间范围 - 动态显示容器 -->
      <div class="custom-time-container">
        <div v-if="showCustomInputs" class="space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <input
              v-model="customStart"
              type="datetime-local"
              class="input--professional--compact w-full text-xs"
              :disabled="disabled"
              @change="updateCustomRange"
              :placeholder="t('common.timeRange.customRange.start')"
            />
            <input
              v-model="customEnd"
              type="datetime-local"
              class="input--professional--compact w-full text-xs"
              :disabled="disabled"
              @change="updateCustomRange"
              :placeholder="t('common.timeRange.customRange.end')"
            />
          </div>
        </div>
      </div>
      
      <!-- 当前选择显示 -->
      <div
        class="text-xs p-1 rounded text-center whitespace-nowrap overflow-hidden text-ellipsis"
        :title="displayRange"
        style="background: var(--ft-background-light); color: var(--ft-text-muted);"
      >
        {{ displayRange }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

interface TimeRange {
  start: Date
  end: Date
  label: string
}

const props = defineProps<{
  modelValue: TimeRange | null
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [range: TimeRange | null]
}>()

const { t } = useI18n()

const timePresets = computed(() => [
  { value: '1d', label: t('common.timeRange.presets.1d') },
  { value: '1w', label: t('common.timeRange.presets.1w') },
  { value: '1m', label: t('common.timeRange.presets.1m') },
  { value: '1y', label: t('common.timeRange.presets.1y') },
  { value: 'custom', label: t('common.timeRange.presets.custom') }
])

const selectedPreset = ref('')
const customStart = ref('')
const customEnd = ref('')
const showCustomInputs = ref(false)

// 计算当前时间范围
const currentRange = computed(() => {
  // 如果没有选择预设，返回null
  if (!selectedPreset.value) {
    return null
  }
  
  const now = new Date()
  let start = new Date()
  let label = ''
  
  switch (selectedPreset.value) {
    case '1d':
      start.setDate(now.getDate() - 1)
      label = t('common.timeRange.labels.past24h')
      break
    case '1w':
      start.setDate(now.getDate() - 7)
      label = t('common.timeRange.labels.past7d')
      break
    case '1m':
      start.setMonth(now.getMonth() - 1)
      label = t('common.timeRange.labels.past30d')
      break
    case '1y':
      start.setFullYear(now.getFullYear() - 1)
      label = t('common.timeRange.labels.past365d')
      break
    case 'custom':
      if (customStart.value && customEnd.value) {
        start = new Date(customStart.value)
        label = t('common.timeRange.customRange.customFormat', { start: formatDate(start), end: formatDate(new Date(customEnd.value)) })
      } else {
        start.setDate(now.getDate() - 1)
        label = t('common.timeRange.labels.past24h')
      }
      break
    default:
      start.setDate(now.getDate() - 1)
      label = t('common.timeRange.labels.past24h')
  }
  
  return {
    start,
    end: now,
    label
  }
})

// 显示范围文本
const displayRange = computed(() => {
  const range = currentRange.value
  if (!range) {
    return t('common.timeRange.pleaseSelect')
  }
  const start = formatDate(range.start)
  const end = formatDate(range.end)
  return `${range.label} (${start} - ${end})`
})

// 选择预设
const selectPreset = (preset: string) => {
  if (props.disabled) return
  
  // 如果点击已选中的预设，则取消选择
  if (selectedPreset.value === preset && preset !== 'custom') {
    selectedPreset.value = ''
    showCustomInputs.value = false
    emit('update:modelValue', null)
    return
  }
  
  if (preset === 'custom') {
    // 点击自定义时切换显示/隐藏状态
    if (selectedPreset.value === 'custom') {
      // 如果已经是自定义状态，则取消选择
      selectedPreset.value = ''
      showCustomInputs.value = false
      emit('update:modelValue', null)
    } else {
      // 切换到自定义状态
      selectedPreset.value = preset
      showCustomInputs.value = true
      emit('update:modelValue', currentRange.value)
    }
  } else {
    selectedPreset.value = preset
    showCustomInputs.value = false
    emit('update:modelValue', currentRange.value)
  }
}

// 更新自定义范围
const updateCustomRange = () => {
  if (props.disabled) return
  
  if (showCustomInputs.value && customStart.value && customEnd.value) {
    const start = new Date(customStart.value)
    const end = new Date(customEnd.value)
    
    if (start < end) {
      emit('update:modelValue', {
        start,
        end,
        label: t('common.timeRange.customRange.customFormat', { start: formatDate(start), end: formatDate(end) })
      })
    }
  }
}

// 格式化日期
const formatDate = (date: Date): string => {
  const locale = useI18n().locale.value
  return date.toLocaleDateString(locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 初始化
const initCustomRange = () => {
  const now = new Date()
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  
  customStart.value = yesterday.toISOString().slice(0, 16)
  customEnd.value = now.toISOString().slice(0, 16)
}

// 监听变化
watch(currentRange, (newRange) => {
  if (!showCustomInputs.value) {
    emit('update:modelValue', newRange)
  }
}, { immediate: false }) // 不立即执行，避免默认值

// 初始化
initCustomRange()
</script>

<style scoped>
.time-selector--professional {
  @apply space-y-3;
}

.btn--professional {
  @apply px-3 py-2 rounded-md text-sm font-medium transition-all duration-200;
  background: var(--ft-surface);
  color: var(--ft-text-primary);
  border: 1px solid var(--ft-border);
}

.btn--professional--compact {
  @apply px-2 py-1 rounded text-xs font-medium transition-all duration-200;
  @apply flex items-center justify-center;
  background: var(--ft-surface);
  color: var(--ft-text-primary);
  border: 1px solid var(--ft-border);
  min-height: 2rem;
}

.btn--primary {
  background: linear-gradient(135deg, 
    rgba(78, 201, 176, 0.05) 0%, 
    rgba(78, 201, 176, 0.02) 100%);
  color: var(--od-primary-light);
  border-color: var(--od-primary);
  box-shadow: 0 0 0 1px rgba(78, 201, 176, 0.2) inset, 
              0 0 8px rgba(78, 201, 176, 0.15);
  font-weight: 500;
}

.btn--primary:hover {
  /* 保持原有样式，不添加额外背景 */
  background: linear-gradient(135deg, 
    rgba(78, 201, 176, 0.05) 0%, 
    rgba(78, 201, 176, 0.02) 100%);
  transform: none;
  box-shadow: 0 0 0 1px rgba(78, 201, 176, 0.2) inset, 
              0 0 8px rgba(78, 201, 176, 0.15);
}

.btn--secondary {
  background: var(--ft-surface);
  color: var(--ft-text-secondary);
}

.btn--secondary:hover {
  background: transparent;
  border-color: rgba(78, 201, 176, 0.5);
  color: var(--od-primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(78, 201, 176, 0.1);
}

.input--professional {
  @apply w-full px-3 py-2 rounded-md text-sm;
  background: var(--ft-background-light);
  color: var(--ft-text-primary);
  border: 1px solid var(--ft-border);
}

.input--professional--compact {
  @apply w-full px-2 py-1 rounded text-xs;
  background: var(--ft-background-light);
  color: var(--ft-text-primary);
  border: 1px solid var(--ft-border);
}

/* 动态高度容器 - 平滑过渡 */
.custom-time-container {
  transition: all 0.2s ease-in-out;
  overflow: hidden;
}

.input--professional:focus,
.input--professional--compact:focus {
  outline: none;
  border-color: var(--ft-primary);
  box-shadow: 0 0 0 2px rgba(78, 201, 176, 0.2);
}

/* 禁用状态样式 */
.time-selector--disabled {
  opacity: 0.5;
  pointer-events: none;
}

.btn--professional--compact:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.input--professional--compact:disabled {
  cursor: not-allowed;
  background: var(--ft-background-muted);
}
</style>
