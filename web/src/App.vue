<template>
  <div id="app" :class="fullThemeClass" class="min-h-screen transition-colors duration-300">
    <router-view />
    <ToastNotification />
  </div>
</template>
 
<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme } from '@/composables/useTheme'
import ToastNotification from '@/components/ui/Toast.vue'

// 初始化主题系统
const { fullThemeClass, initTheme } = useTheme()

// 应用启动时初始化
onMounted(() => {
  initTheme()
})
</script>

<style>
/* 确保主题变量在全局可用 */
#app {
  background-color: var(--ft-background);
  color: var(--ft-text-primary);
}

/* 平滑过渡效果 */
* {
  transition-property: background-color, border-color, color, fill, stroke;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 200ms;
}
</style> 