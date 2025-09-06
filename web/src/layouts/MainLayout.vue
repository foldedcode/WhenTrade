<template>
  <div class="h-screen overflow-hidden" style="background: var(--od-background); color: var(--od-text-primary);">
    <!-- 精致顶部导航栏 -->
    <nav class="sticky top-0 z-50 backdrop-blur-sm border-b" style="background: rgba(30, 30, 30, 0.95); border-color: var(--od-border);">
      <div class="max-w-full mx-auto px-4 lg:px-6">
        <div class="flex justify-between h-14 items-center">
          <!-- 品牌区域 - 终端风格 -->
          <div class="flex items-center space-x-4">
            <router-link to="/" class="terminal-brand-link">
              <div class="terminal-brand">
                <div class="terminal-prompt">
                  <span class="terminal-user">root@finance</span>
                  <span class="terminal-separator">:</span>
                  <span class="terminal-path">~</span>
                  <span class="terminal-symbol">$</span>
                  <span class="terminal-command">when.trade</span>
                  <span class="terminal-cursor"></span>
                </div>
                <div class="terminal-subtitle">
                  <span class="terminal-output">{{ $t('common.subtitle') }}</span>
                </div>
              </div>
            </router-link>
            
            <!-- 状态指示器 -->
            <div class="hidden md:flex items-center space-x-4">
              <div class="flex items-center space-x-2">
                <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span class="text-xs" style="color: var(--od-text-muted)">{{ t('common.status.online') }}</span>
              </div>
              <div class="text-xs" style="color: var(--od-text-muted)">
                {{ currentTime }}
              </div>
            </div>
          </div>
          
          <!-- 工具栏 -->
          <div class="flex items-center space-x-2">
            <button
              @click.stop="handleToggleColorScheme"
              class="theme-toggle-btn"
              :title="$t('common.theme.toggle')"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path v-if="currentTheme.isDark" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </button>
            <ColorSchemeSwitcher />
            <LanguageSwitcher />
            <!-- 用户菜单已禁用 -->
          </div>
        </div>
      </div>
    </nav>

    <!-- 主内容区域 -->
    <main class="main-content h-[calc(100vh-3.5rem)] overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import ColorSchemeSwitcher from '@/components/common/ColorSchemeSwitcher.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
// import UserMenu from '@/components/common/UserMenu.vue' // 已禁用
import { useTheme } from '@/composables/useTheme'

const { t } = useI18n()
const { getCurrentTheme, toggleColorScheme } = useTheme()
const currentTheme = getCurrentTheme

// 时间显示
const currentTime = ref('')
let timeInterval: number | null = null

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 直接切换主题，不需要防抖
const handleToggleColorScheme = () => {
  // 立即执行切换
  toggleColorScheme()
}

onMounted(() => {
  updateTime()
  timeInterval = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval !== null) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
/* 终端品牌样式 */
.terminal-brand-link {
  @apply no-underline;
}

.terminal-brand {
  font-family: 'Proto Mono', monospace;
  background: #0a0a0a;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 8px 12px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.5);
  transition: all 0.2s;
}

.terminal-brand:hover {
  border-color: #444;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.5), 0 0 10px rgba(0, 255, 0, 0.1);
}

.terminal-prompt {
  font-size: 13px;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 2px;
}

.terminal-user {
  color: #00ff00;
  font-weight: bold;
}

.terminal-separator {
  color: #ffffff;
}

.terminal-path {
  color: #00bfff;
  font-weight: bold;
}

.terminal-symbol {
  color: #ffffff;
  margin: 0 4px;
}

.terminal-command {
  color: #ffff00;
  font-weight: bold;
}

.terminal-cursor {
  display: inline-block;
  width: 8px;
  height: 16px;
  background: #00ff00;
  margin-left: 2px;
  animation: blink 1s infinite;
}

.terminal-subtitle {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.2;
}

.terminal-output {
  color: #888;
  font-style: italic;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Logo 品牌样式 */
.logo-brand {
  @apply flex items-center cursor-pointer transition-opacity no-underline;
}

.logo-brand:hover {
  opacity: 0.8;
}

/* 主题切换按钮 */
.theme-toggle-btn {
  @apply p-2 rounded-lg transition-all;
  background: var(--od-button-ghost-bg);
  color: var(--od-text-secondary);
}

.theme-toggle-btn:hover {
  background: var(--od-button-ghost-hover);
  color: var(--od-text-primary);
}

/* 主内容区域 */
.main-content {
  background: var(--od-background);
}
</style>