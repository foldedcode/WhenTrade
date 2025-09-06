<template>
  <div class="professional-dropdown" :class="{ 'is-open': isOpen }" ref="dropdownRef">
    <!-- 触发器 -->
    <button
      @click="toggleDropdown"
      class="dropdown-trigger"
      :class="[
        { 'is-active': isOpen },
        `dropdown-trigger--${size}`
      ]"
      :disabled="disabled"
      :aria-expanded="isOpen"
      :aria-haspopup="true"
    >
      <div class="trigger-content">
        <!-- 选中项显示 -->
        <div class="selected-item" v-if="selectedOption">
          <LLMProviderLogo 
            v-if="showLogo && selectedOption.provider" 
            :provider="selectedOption.provider" 
            size="xs" 
            class="mr-2"
          />
          <span class="selected-text" :title="selectedOption.label">{{ selectedOption.label }}</span>
        </div>
        <div class="placeholder" v-else>
          {{ placeholder }}
        </div>
        
        <!-- 下拉箭头 -->
        <div class="dropdown-arrow" :class="{ 'is-rotated': isOpen }">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
    </button>

    <!-- 下拉面板 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="dropdown-panel"
        :style="panelStyle"
        ref="panelRef"
      >
        <div class="panel-content">
          <!-- 搜索框 -->
          <div v-if="searchable" class="search-container">
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              :placeholder="searchPlaceholder"
              @click.stop
            />
            <div class="search-icon">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="11" cy="11" r="8" stroke-width="2"/>
                <path d="m21 21-4.35-4.35" stroke-width="2"/>
              </svg>
            </div>
          </div>

          <!-- 选项列表 -->
          <div class="options-container" :style="{ maxHeight: props.maxHeight }">
            <div
              v-for="option in filteredOptions"
              :key="option.value"
              @click="selectOption(option)"
              class="dropdown-option"
              :class="{ 'is-selected': option.value === modelValue }"
            >
              <div class="option-content">
                <!-- 提供商Logo -->
                <LLMProviderLogo 
                  v-if="showLogo && option.provider" 
                  :provider="option.provider" 
                  size="sm" 
                  class="option-logo"
                />
                
                <!-- 选项图标 -->
                <div v-else-if="option.icon" class="option-icon">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path :d="option.icon" />
                  </svg>
                </div>

                <!-- 选项内容 -->
                <div class="option-text">
                  <div class="option-label" :title="option.label">{{ option.label }}</div>
                  <div v-if="option.description" class="option-description" :title="option.description">
                    {{ option.description }}
                  </div>
                </div>

                <!-- 选中标识 -->
                <div v-if="option.value === modelValue" class="selected-indicator">
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <polyline points="20,6 9,17 4,12" stroke-width="2"/>
                  </svg>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="filteredOptions.length === 0" class="empty-state">
              <div class="empty-icon">
                <svg class="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <circle cx="11" cy="11" r="8" stroke-width="2"/>
                  <path d="m21 21-4.35-4.35" stroke-width="2"/>
                </svg>
              </div>
              <div class="empty-text">{{ emptyText }}</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import LLMProviderLogo from './LLMProviderLogo.vue'

const { t } = useI18n()

interface DropdownOption {
  value: string | number
  label: string
  description?: string
  icon?: string
  provider?: string
  disabled?: boolean
}

interface Props {
  modelValue: string | number | null
  options: DropdownOption[]
  placeholder?: string
  searchable?: boolean
  searchPlaceholder?: string
  emptyText?: string
  disabled?: boolean
  showLogo?: boolean
  maxHeight?: string
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请选择',
  searchPlaceholder: '搜索选项...',
  emptyText: '暂无匹配选项',
  disabled: false,
  showLogo: false,
  maxHeight: '240px',
  size: 'md'
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
  'change': [option: DropdownOption | null]
}>()

// 响应式状态
const isOpen = ref(false)
const searchQuery = ref('')
const dropdownRef = ref<HTMLElement>()
const panelRef = ref<HTMLElement>()
const panelStyle = ref({})

// 计算属性
const selectedOption = computed(() => {
  return props.options.find(option => option.value === props.modelValue) || null
})

const filteredOptions = computed(() => {
  if (!props.searchable || !searchQuery.value) {
    return props.options.filter(option => !option.disabled)
  }
  
  const query = searchQuery.value.toLowerCase()
  return props.options.filter(option => 
    !option.disabled &&
    (option.label.toLowerCase().includes(query) ||
     option.description?.toLowerCase().includes(query))
  )
})

// 方法
const toggleDropdown = () => {
  if (props.disabled) return
  
  if (isOpen.value) {
    closeDropdown()
  } else {
    openDropdown()
  }
}

const openDropdown = async () => {
  isOpen.value = true
  await nextTick()
  updatePanelPosition()
  searchQuery.value = ''
}

const closeDropdown = () => {
  isOpen.value = false
  searchQuery.value = ''
}

const selectOption = (option: DropdownOption) => {
  if (option.disabled) return
  
  emit('update:modelValue', option.value)
  emit('change', option)
  closeDropdown()
}

const updatePanelPosition = () => {
  if (!dropdownRef.value || !panelRef.value) return
  
  const trigger = dropdownRef.value.getBoundingClientRect()
  const panel = panelRef.value
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight
  }
  
  let top = trigger.bottom + 8
  let left = trigger.left
  
  // 检查是否超出视口底部
  const panelHeight = Math.min(parseInt(props.maxHeight), 300)
  if (top + panelHeight > viewport.height) {
    top = trigger.top - panelHeight - 8
  }
  
  // 计算面板宽度，确保不超出视窗
  // 对于有logo的下拉菜单（如LLM提供商），适当增加宽度但不要过宽
  const minWidth = props.showLogo ? Math.max(trigger.width, 200) : trigger.width
  const maxWidth = props.showLogo ? 240 : 300  // 进一步减小最大宽度
  const panelWidth = Math.min(minWidth, maxWidth, viewport.width - 32)
  
  // 检查是否超出视口右侧
  if (left + panelWidth > viewport.width) {
    left = viewport.width - panelWidth - 16
  }
  
  panelStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${panelWidth}px`,
    zIndex: 9999
  }
}

// 点击外部关闭
const handleClickOutside = (event: Event) => {
  if (!dropdownRef.value || !panelRef.value) return
  
  const target = event.target as Node
  if (!dropdownRef.value.contains(target) && !panelRef.value.contains(target)) {
    closeDropdown()
  }
}

// 键盘事件
const handleKeydown = (event: KeyboardEvent) => {
  if (!isOpen.value) return
  
  switch (event.key) {
    case 'Escape':
      closeDropdown()
      break
    case 'ArrowDown':
      event.preventDefault()
      break
    case 'ArrowUp':
      event.preventDefault()
      break
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', updatePanelPosition)
  window.addEventListener('scroll', updatePanelPosition)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', updatePanelPosition)
  window.removeEventListener('scroll', updatePanelPosition)
})

// 监听打开状态变化
watch(isOpen, (newValue) => {
  if (newValue) {
    nextTick(() => {
      updatePanelPosition()
    })
  }
})
</script>

<style scoped>
/* 专业下拉框容器 */
.professional-dropdown {
  @apply relative;
}

/* 触发器 */
.dropdown-trigger {
  @apply w-full text-left transition-all duration-200 cursor-pointer;
  @apply border rounded-lg outline-none;
  background: var(--ft-surface);
  border-color: var(--ft-border);
  color: var(--ft-text-primary);
}

/* 尺寸变体 */
.dropdown-trigger--sm {
  @apply px-2 py-1 text-sm;
}

.dropdown-trigger--md {
  @apply px-3 py-2 text-sm;
}

.dropdown-trigger--lg {
  @apply px-4 py-3 text-base;
}

.dropdown-trigger:hover {
  border-color: var(--ft-border-light);
  background: var(--ft-surface-light);
}

.dropdown-trigger.is-active,
.dropdown-trigger:focus {
  border-color: var(--ft-primary);
  box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2);
}

.dropdown-trigger:disabled {
  @apply cursor-not-allowed opacity-50;
}

/* 触发器内容 */
.trigger-content {
  @apply flex items-center justify-between;
}

.selected-item {
  @apply flex items-center flex-1 min-w-0;
}

.selected-text {
  @apply truncate;
}

.placeholder {
  @apply flex-1 truncate whitespace-nowrap;
  color: var(--ft-text-muted);
}

/* 下拉箭头 */
.dropdown-arrow {
  @apply transition-transform duration-200 ml-2;
  color: var(--ft-text-muted);
}

.dropdown-arrow.is-rotated {
  transform: rotate(180deg);
}

/* 下拉面板 */
.dropdown-panel {
  @apply border rounded-lg shadow-xl;
  background: var(--ft-surface);
  border-color: var(--ft-border);
  box-shadow: var(--ft-shadow-xl);
}

.panel-content {
  @apply overflow-hidden rounded-lg;
}

/* 搜索框 */
.search-container {
  @apply relative p-2 border-b;
  border-color: var(--ft-border);
}

.search-input {
  @apply w-full pl-8 pr-3 py-2 text-sm border rounded-md outline-none;
  background: var(--ft-background);
  border-color: var(--ft-border);
  color: var(--ft-text-primary);
}

.search-input:focus {
  border-color: var(--ft-primary);
}

.search-input::placeholder {
  color: var(--ft-text-muted);
}

.search-icon {
  @apply absolute left-4 top-1/2 transform -translate-y-1/2;
  color: var(--ft-text-muted);
}

/* 选项容器 */
.options-container {
  @apply overflow-y-auto;
  scrollbar-width: thin;
  scrollbar-color: var(--ft-border) transparent;
}

.options-container::-webkit-scrollbar {
  width: 6px;
}

.options-container::-webkit-scrollbar-track {
  background: transparent;
}

.options-container::-webkit-scrollbar-thumb {
  background: var(--ft-border);
  border-radius: 3px;
}

.options-container::-webkit-scrollbar-thumb:hover {
  background: var(--ft-border-light);
}

/* 下拉选项 */
.dropdown-option {
  @apply px-3 py-2 cursor-pointer transition-all duration-150;
}

.dropdown-option:hover {
  background: var(--ft-interactive-hover);
}

.dropdown-option.is-selected {
  background: var(--ft-interactive-active);
  color: var(--ft-primary);
}

.option-content {
  @apply flex items-center space-x-3;
}

.option-logo {
  @apply flex-shrink-0;
}

.option-icon {
  @apply flex-shrink-0 w-8 h-8 rounded flex items-center justify-center;
  background: var(--ft-surface-light);
  color: var(--ft-text-muted);
}

.option-text {
  @apply flex-1 min-w-0;
}

.option-label {
  @apply text-sm font-medium truncate;
  color: var(--ft-text-primary);
}

.option-description {
  @apply text-xs truncate;
  color: var(--ft-text-muted);
}

.selected-indicator {
  @apply flex-shrink-0;
  color: var(--ft-primary);
}

/* 空状态 */
.empty-state {
  @apply flex flex-col items-center justify-center py-8 px-4;
}

.empty-icon {
  @apply mb-2;
  color: var(--ft-text-muted);
}

.empty-text {
  @apply text-sm text-center;
  color: var(--ft-text-muted);
}

/* 响应式调整 */
@media (max-width: 640px) {
  .dropdown-panel {
    @apply mx-4;
    max-width: calc(100vw - 32px);
  }
}

/* 动画效果 */
.dropdown-panel {
  animation: fadeInScale 0.2s ease-out;
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .dropdown-trigger {
    border-width: 2px;
  }
  
  .dropdown-option:hover {
    outline: 2px solid var(--ft-primary);
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .dropdown-trigger,
  .dropdown-arrow,
  .dropdown-option {
    transition: none;
  }
  
  .dropdown-panel {
    animation: none;
  }
}
</style>
