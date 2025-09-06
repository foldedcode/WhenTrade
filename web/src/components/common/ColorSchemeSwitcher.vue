<template>
  <div class="color-scheme-switcher">
    <!-- 主题切换按钮 -->
    <button
      @click.stop="togglePanel"
      class="theme-trigger"
      :class="{ 'is-active': isOpen }"
      :title="t('common.theme.colorScheme')"
    >
      <div class="theme-trigger__content">
        <div class="theme-trigger__icon">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none">
            <defs>
              <linearGradient id="rainbow" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#ff0000"/>
                <stop offset="16.67%" style="stop-color:#ff8000"/>
                <stop offset="33.33%" style="stop-color:#ffff00"/>
                <stop offset="50%" style="stop-color:#00ff00"/>
                <stop offset="66.67%" style="stop-color:#0080ff"/>
                <stop offset="83.33%" style="stop-color:#8000ff"/>
                <stop offset="100%" style="stop-color:#ff0080"/>
              </linearGradient>
            </defs>
            <circle cx="12" cy="12" r="3" fill="url(#rainbow)"/>
            <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" stroke="url(#rainbow)" stroke-width="2"/>
          </svg>
        </div>
      </div>
    </button>

    <!-- 主题选择面板 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="theme-panel"
        :style="panelStyle"
        ref="panelRef"
      >
        <!-- 箭头指示器 -->
        <div class="theme-panel__arrow"></div>
        
        <div class="simple-color-panel">
          <div class="color-list">
            <div
              v-for="scheme in colorSchemes"
              :key="scheme.id"
              @click="selectColorScheme(scheme.id)"
              class="color-row"
              :class="{ 'active': currentColorMode === scheme.id }"
            >
              <div class="color-preview" :style="{ backgroundColor: scheme.colors[0] }"></div>
              <span class="color-name">{{ t(`common.colorSchemes.${scheme.id}`) }}</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 遮罩层 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="theme-overlay"
        @click="closePanel"
      ></div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'

interface ColorScheme {
  id: string
  name: string
  description: string
  colors: string[]
}

// 使用 i18n
const { t } = useI18n()

// 响应式状态
const isOpen = ref(false)
const panelRef = ref<HTMLElement>()
const currentColorMode = ref('professional')
const panelStyle = ref({})

// 配色方案定义 - 高级配色
const colorSchemes: ColorScheme[] = [
  {
    id: 'professional',
    name: '',
    description: 'Luxury Financial Theme',
    colors: ['#D4AF37', '#F7E7CE', '#1A1A1A', '#3A3A3A']
  },
  {
    id: 'standard',
    name: '',
    description: 'Deep Professional Theme',
    colors: ['#0047AB', '#4169E1', '#0F0F0F', '#2A2A2A']
  },
  {
    id: 'success',
    name: '',
    description: 'Elegant Success Theme',
    colors: ['#50C878', '#2E8B57', '#161616', '#323232']
  },
  {
    id: 'tech',
    name: '',
    description: 'Mysterious Tech Theme',
    colors: ['#9966CC', '#7B68EE', '#141414', '#2E2E2E']
  },
  {
    id: 'alert',
    name: '',
    description: 'Noble Alert Theme',
    colors: ['#DC143C', '#B22222', '#181818', '#363636']
  },
  {
    id: 'cyan',
    name: '',
    description: 'Elegant Fresh Theme',
    colors: ['#0ABAB5', '#00CED1', '#121212', '#2C2C2C']
  },
  {
    id: 'orange',
    name: '',
    description: 'Luxury Vibrant Theme',
    colors: ['#FF6600', '#FF8C00', '#151515', '#303030']
  },
  {
    id: 'rose',
    name: '',
    description: 'Gentle Luxury Theme',
    colors: ['#B76E79', '#F4C2C2', '#1A1616', '#342E2E']
  },
  {
    id: 'silver',
    name: '',
    description: 'Modern Minimal Theme',
    colors: ['#C0C0C0', '#E5E5E5', '#141414', '#2A2A2A']
  },
  {
    id: 'emerald',
    name: '',
    description: 'Natural Vitality Theme',
    colors: ['#0BDA51', '#50C878', '#0F1F0F', '#1F2F1F']
  },
  {
    id: 'sapphire',
    name: '',
    description: 'Noble Elegant Theme',
    colors: ['#0F52BA', '#4169E1', '#0A0F1A', '#1A2F4A']
  },
  {
    id: 'amber',
    name: '',
    description: 'Warm Retro Theme',
    colors: ['#FFBF00', '#FFC000', '#1A1400', '#2A2400']
  },
  {
    id: 'obsidian',
    name: '',
    description: 'Deep Mysterious Theme',
    colors: ['#3D3D3D', '#5C5C5C', '#0A0A0A', '#1A1A1A']
  }
]

// 方法
const togglePanel = (event?: Event) => {
  // 阻止事件冒泡
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
  const trigger = document.querySelector('.theme-trigger')
  if (trigger) {
    const triggerRect = trigger.getBoundingClientRect()
    panelStyle.value = {
      position: 'fixed',
      top: `${triggerRect.bottom + 8}px`,
      left: `${triggerRect.right - 180}px`, // 预估宽度
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

const selectColorScheme = (schemeId: string) => {
  currentColorMode.value = schemeId
  
  // 立即应用配色方案
  document.documentElement.setAttribute('data-color-mode', schemeId)
  
  // 强制浏览器重新计算样式
  document.documentElement.classList.add('theme-switching')
  requestAnimationFrame(() => {
    document.documentElement.classList.remove('theme-switching')
  })
  
  // 保存到本地存储（使用系统统一的键名）
  localStorage.setItem('when-trade-color-mode', schemeId)
  localStorage.setItem('colorScheme', schemeId) // 保持向后兼容
  
  // 触发主题变更事件
  window.dispatchEvent(new CustomEvent('colorModeChange', { 
    detail: { mode: schemeId } 
  }))
  
  // 快速关闭面板
  setTimeout(() => {
    closePanel()
  }, 200)
}

const resetToDefault = () => {
  selectColorScheme('professional')
}

const randomizeScheme = () => {
  const availableSchemes = colorSchemes.filter(s => s.id !== currentColorMode.value)
  const randomScheme = availableSchemes[Math.floor(Math.random() * availableSchemes.length)]
  selectColorScheme(randomScheme.id)
}

const getCurrentSchemeColors = () => {
  const scheme = colorSchemes.find(s => s.id === currentColorMode.value)
  return scheme ? scheme.colors : colorSchemes[0].colors
}

const getCurrentSchemeName = () => {
  const scheme = colorSchemes.find(s => s.id === currentColorMode.value)
  return scheme ? scheme.name : colorSchemes[0].name
}

const updatePanelPosition = () => {
  const trigger = document.querySelector('.theme-trigger')
  if (!trigger || !panelRef.value) return
  
  const triggerRect = trigger.getBoundingClientRect()
  
  // 使用 ResizeObserver 或多次重试确保获取正确宽度
  const actualWidth = panelRef.value.offsetWidth
  const computedStyle = window.getComputedStyle(panelRef.value)
  const hasWidth = actualWidth > 0 && computedStyle.display !== 'none'
  
  if (!hasWidth) {
    // 延迟重试，等待CSS完全应用
    setTimeout(updatePanelPosition, 10)
    return
  }
  
  const panelWidth = actualWidth
  const isMobile = window.innerWidth <= 768
  const panelMaxHeight = isMobile ? 300 : 260  // 移动端高度更小
  const gap = 8 // 面板与按钮的间距
  
  // 计算面板位置 - 与按钮右对齐
  let left = triggerRect.right - panelWidth
  let top = triggerRect.bottom + gap
  
  // 移动端特殊处理
  if (isMobile) {
    // 保持右对齐
    left = window.innerWidth - panelWidth - 16
  } else {
    // 确保面板不超出视窗右边界
    if (left + panelWidth > window.innerWidth) {
      left = window.innerWidth - panelWidth - 16
    }
    
    // 确保面板不超出视窗左边界
    if (left < 16) {
      left = 16
    }
  }
  
  // 如果面板底部超出视窗，则显示在按钮上方
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
  const trigger = document.querySelector('.theme-trigger')
  
  // 如果点击的是触发按钮或面板内部，不关闭
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
  // 从DOM获取当前配色方案（已由theme.ts初始化）
  const currentScheme = document.documentElement.getAttribute('data-color-mode') || 'professional'
  currentColorMode.value = currentScheme
  
  // 延迟添加事件监听器，避免立即触发
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
/* 主题触发器 */
.theme-trigger {
  @apply px-2 py-1.5 rounded-md transition-all duration-200 cursor-pointer;
  background: transparent;
  border: 1px solid transparent;
  color: var(--ft-text-secondary);
  height: 32px;
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-trigger:hover {
  background: var(--od-background-alt);
  border-color: var(--od-border);
  color: var(--od-text-primary);
}

.theme-trigger.is-active {
  background: var(--ft-interactive-active);
  border-color: var(--ft-primary);
  color: var(--ft-primary);
}

.theme-trigger__content {
  @apply flex items-center space-x-1.5;
}

.theme-trigger__icon {
  @apply transition-all duration-200;
}

.theme-trigger__icon svg {
  @apply w-3.5 h-3.5;
}

.theme-trigger__text {
  @apply text-xs font-medium;
}

/* 主题面板 */
.theme-panel {
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
.theme-panel__arrow {
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

/* 简单配色面板 - 终端风格 */
.simple-color-panel {
  padding: 10px;
  border: 1px solid var(--od-border);
  border-radius: 4px;
  font-family: 'Proto Mono', monospace;
  box-shadow: 0 0 20px rgba(0, 255, 0, 0.1);
  background: var(--od-background);
  max-height: 400px;
  overflow-y: auto;
}


/* 添加终端闪烁光标 */
.simple-color-panel::after {
  content: '█';
  position: absolute;
  bottom: 6px;
  right: 8px;
  font-size: 8px;
  color: var(--od-primary);
  animation: blink 1s infinite;
  opacity: 0.6;
}

.color-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.color-row {
  display: flex;
  align-items: center;
  padding: 4px 6px;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
}

.color-row:hover {
  background: var(--od-background-alt);
}

.color-row.active {
  background: var(--od-background-light);
  border-left: 2px solid var(--od-primary);
  padding-left: 4px;
}

.color-row.active::after {
  content: ' *';
  margin-left: auto;
  color: var(--od-primary);
  font-size: 10px;
  font-weight: bold;
}

.color-preview {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  margin-right: 8px;
  border: 1px solid var(--od-border);
  box-shadow: 0 0 4px rgba(0,0,0,0.5);
}

.color-name {
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

/* 添加终端扫描线效果 */
.simple-color-panel {
  position: relative;
  background: repeating-linear-gradient(
    transparent,
    transparent 1px,
    rgba(0, 255, 0, 0.03) 1px,
    rgba(0, 255, 0, 0.03) 2px
  ), var(--od-background);
}

/* 遮罩层 */
.theme-overlay {
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
  .theme-trigger {
    width: 36px;
    height: 30px;
  }
  
  .theme-panel {
    @apply max-w-none;
    width: auto !important;
    min-width: 180px;
    max-width: calc(100vw - 32px) !important;
    right: 16px !important;
    left: auto !important;
  }
  
  .theme-panel__arrow {
    right: 12px;
    left: auto;
  }
  
  .simple-color-panel {
    width: auto;
    min-width: 160px;
    max-height: 300px;
    padding: 8px;
  }
  
  .color-row {
    padding: 6px 8px;
  }
  
  .color-preview {
    width: 16px;
    height: 16px;
    margin-right: 10px;
  }
  
  .color-name {
    font-size: 12px;
  }
}
</style>