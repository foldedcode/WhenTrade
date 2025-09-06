<template>
  <div class="relative">
    <button
      @click="toggleDropdown"
      class="language-switch-btn flex items-center space-x-1.5 px-2 py-1.5"
      :title="$t('common.language.switch')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
      </svg>
    </button>

    <!-- 语言选择面板 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="language-panel"
        :style="panelStyle"
        ref="panelRef"
      >
        <!-- 箭头指示器 -->
        <div class="language-panel__arrow"></div>
        
        <div class="simple-language-panel">
          <div class="language-list">
            <div
              v-for="lang in languages"
              :key="lang.code"
              @click="switchLanguage(lang.code)"
              class="lang-row"
              :class="{ 'active': locale === lang.code }"
            >
              <span class="lang-flag">{{ lang.flag }}</span>
              <span class="lang-label">{{ lang.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 遮罩层 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="language-overlay"
        @click="closePanel"
      ></div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { saveLocale } from '@/locales'

const { locale } = useI18n()
const isOpen = ref(false)
const panelRef = ref<HTMLElement>()
const panelStyle = ref({})

const languages = [
  { code: 'zh-CN', label: '简体中文', native: '中文', flag: '🇨🇳' },
  { code: 'en-US', label: 'English', native: 'English', flag: '🇺🇸' }
]

const currentLanguage = computed(() => 
  languages.find(lang => lang.code === locale.value) || languages[0]
)

const toggleDropdown = async (event?: Event) => {
  if (event) {
    event.stopPropagation()
  }
  
  if (isOpen.value) {
    closePanel()
  } else {
    openPanel()
  }
}

const openPanel = async () => {
  // 先预设一个基础位置避免闪烁
  const trigger = document.querySelector('.language-switch-btn')
  if (trigger) {
    const triggerRect = trigger.getBoundingClientRect()
    panelStyle.value = {
      position: 'fixed',
      top: `${triggerRect.bottom + 8}px`,
      left: `${triggerRect.right - 160}px`, // 预估宽度
      opacity: '0', // 先隐藏
      zIndex: 9999
    }
  }
  
  isOpen.value = true
  await nextTick()
  updatePanelPosition()
  
  // 显示面板
  setTimeout(() => {
    if (panelStyle.value.opacity === '0') {
      panelStyle.value = { ...panelStyle.value, opacity: '1' }
    }
  }, 20)
}

const closePanel = () => {
  isOpen.value = false
}

const switchLanguage = (code: string) => {
  locale.value = code
  
  // 持久化语言设置
  localStorage.setItem('when-trade-locale', code)
  
  // 保存语言偏好到 i18n
  saveLocale(code)
  
  setTimeout(() => {
    closePanel()
    // 某些情况下需要刷新页面以确保所有翻译都更新
    // 特别是动态生成的内容
    if (import.meta.env.DEV) {
      console.log('语言已切换至:', code)
    }
  }, 200)
}

const updatePanelPosition = () => {
  const trigger = document.querySelector('.language-switch-btn')
  if (!trigger || !panelRef.value) return
  
  const triggerRect = trigger.getBoundingClientRect()
  
  // 使用多次重试确保获取正确宽度
  const actualWidth = panelRef.value.offsetWidth
  const computedStyle = window.getComputedStyle(panelRef.value)
  const hasWidth = actualWidth > 0 && computedStyle.display !== 'none'
  
  if (!hasWidth) {
    // 延迟重试，等待CSS完全应用
    setTimeout(updatePanelPosition, 10)
    return
  }
  
  const panelWidth = actualWidth
  const panelMaxHeight = 220
  const gap = 8
  const isMobile = window.innerWidth <= 768
  
  let left = triggerRect.right - panelWidth
  let top = triggerRect.bottom + gap
  
  // 移动端特殊处理
  if (isMobile) {
    // 保持右对齐
    left = window.innerWidth - panelWidth - 16
  } else {
    if (left + panelWidth > window.innerWidth) {
      left = window.innerWidth - panelWidth - 16
    }
    
    if (left < 16) {
      left = 16
    }
  }
  
  if (top + panelMaxHeight > window.innerHeight - 16) {
    top = triggerRect.top - panelMaxHeight - gap
  }
  
  panelStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    maxHeight: `${panelMaxHeight}px`,
    opacity: '1',
    zIndex: 9999
  }
}

// 点击外部关闭
const handleClickOutside = (event: Event) => {
  if (!isOpen.value || !panelRef.value) return
  
  const target = event.target as Node
  const trigger = document.querySelector('.language-switch-btn')
  
  if (trigger?.contains(target) || panelRef.value.contains(target)) {
    return
  }
  
  closePanel()
}

// 键盘事件
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && isOpen.value) {
    closePanel()
  }
}

// 生命周期
onMounted(() => {
  setTimeout(() => {
    document.addEventListener('click', handleClickOutside)
    document.addEventListener('keydown', handleKeydown)
    window.addEventListener('resize', updatePanelPosition)
  }, 100)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', updatePanelPosition)
})
</script>

<style scoped>
.language-switch-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  height: 32px;
  width: 40px;
  color: var(--od-text-muted);
  transition: all 0.2s ease;
  justify-content: center;
}

.language-switch-btn:hover {
  background: var(--od-background-alt);
  border-color: var(--od-border);
  color: var(--od-text-primary);
}

/* 语言面板 */
.language-panel {
  @apply rounded-lg shadow-xl border;
  background: var(--ft-surface);
  border-color: var(--ft-border);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  animation: fadeInDown 0.2s ease-out;
  position: relative;
  min-width: fit-content;
  overflow: visible;
}

/* 箭头指示器 */
.language-panel__arrow {
  position: absolute;
  top: -6px;
  right: 24px;
  width: 12px;
  height: 12px;
  background: var(--ft-surface);
  border-left: 1px solid var(--ft-border);
  border-top: 1px solid var(--ft-border);
  transform: rotate(45deg);
}

/* 简单语言面板 - 终端风格 */
.simple-language-panel {
  padding: 10px;
  border: 1px solid var(--od-border);
  border-radius: 4px;
  font-family: 'Proto Mono', monospace;
  box-shadow: 0 0 20px rgba(0, 255, 0, 0.1);
  position: relative;
  background: repeating-linear-gradient(
    transparent,
    transparent 1px,
    rgba(0, 255, 0, 0.03) 1px,
    rgba(0, 255, 0, 0.03) 2px
  ), var(--od-background);
}


/* 添加终端闪烁光标 */
.simple-language-panel::after {
  content: '█';
  position: absolute;
  bottom: 6px;
  right: 8px;
  font-size: 8px;
  color: var(--od-primary);
  animation: blink 1s infinite;
  opacity: 0.6;
}

.language-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.lang-row {
  display: flex;
  align-items: center;
  padding: 4px 6px;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
}

.lang-row:hover {
  background: var(--od-background-alt);
}

.lang-row.active {
  background: var(--od-background-light);
  border-left: 2px solid var(--od-primary);
  padding-left: 4px;
}

.lang-row.active::after {
  content: ' *';
  margin-left: auto;
  color: var(--od-primary);
  font-size: 10px;
  font-weight: bold;
}

.lang-flag {
  font-size: 14px;
  margin-right: 8px;
}

.lang-label {
  font-size: 11px;
  color: var(--od-text-primary);
  white-space: nowrap;
  font-family: 'Proto Mono', monospace;
  text-transform: lowercase;
  font-weight: 500;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 遮罩层 */
.language-overlay {
  @apply fixed inset-0 bg-black bg-opacity-30;
  z-index: 9998;
  backdrop-filter: blur(2px);
}

/* 动画 */
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .language-switch-btn {
    width: 36px;
    height: 30px;
  }
  
  .language-panel {
    @apply max-w-none;
    width: auto !important;
    min-width: 160px;
    max-width: calc(100vw - 32px) !important;
    right: 16px !important;
    left: auto !important;
  }
  
  .language-panel__arrow {
    right: 12px;
    left: auto;
  }
  
  .simple-language-panel {
    width: auto;
    min-width: 140px;
    padding: 8px;
  }
  
  .lang-row {
    padding: 6px 8px;
  }
  
  .lang-flag {
    font-size: 16px;
    margin-right: 10px;
  }
  
  .lang-label {
    font-size: 12px;
  }
}
</style>
