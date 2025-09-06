<template>
  <i 
    :class="['pixelarticons-' + iconName, sizeClass]"
    :style="customStyle"
  ></i>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  name: string
  size?: number | string
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 24
})

// 映射旧图标名称到 pixelarticons 的名称
const iconMapping: Record<string, string> = {
  // 基础图标
  'home': 'home',
  'user': 'user',
  'users': 'users',
  'settings': 'gear',
  'wrench': 'wrench',
  'shield': 'shield',
  'bell': 'notification',
  'key': 'key',
  'wallet': 'wallet',
  'credit-card': 'credit-card',
  
  // 分析相关
  'target': 'bullseye',
  'layers': 'layers',
  'cpu': 'device-laptop',
  'grid': 'grid',
  'chart-bar': 'chart',
  'activity': 'pulse',
  
  // 操作图标
  'x': 'close',
  'check': 'check',
  'plus': 'plus',
  'edit': 'edit',
  'trash': 'trash',
  'copy': 'copy',
  'download': 'download',
  'external-link': 'external-link',
  'eye': 'eye',
  'refresh': 'reload',
  'play': 'play',
  'pause': 'pause',
  
  // 其他
  'star': 'star',
  'crown': 'crown',
  'package': 'box',
  'receipt': 'receipt',
  'mail': 'mail',
  'clock': 'clock',
  'camera': 'camera',
  'desktop': 'device-desktop',
  'mobile': 'device-phone',
  'zap': 'zap',
  'repeat': 'reload',
  'arrow-up-right': 'arrow-right-up',
  'arrow-down-left': 'arrow-left-down',
  'beaker': 'flask',
  'cube': 'box',
  'chat': 'message',
  'loading': 'loader',
  'loader': 'loader',
  'shield-check': 'shield-check',
  'unlink': 'link-none',
  'payment': 'coin',
  'bitcoin': 'coin',
  'paypal': 'coin',
  'refresh-cw': 'reload',
  'share': 'share',
  'check-circle': 'check',
  'link': 'link',
  
  // Heroicons 兼容
  'heroicons:arrow-path': 'reload',
  'heroicons:check': 'check'
}

const iconName = computed(() => {
  return iconMapping[props.name] || props.name
})

const sizeClass = computed(() => {
  const sizeNumber = typeof props.size === 'string' ? parseInt(props.size) : props.size
  if (sizeNumber <= 16) return 'text-base'
  if (sizeNumber <= 20) return 'text-lg'
  if (sizeNumber <= 24) return 'text-xl'
  if (sizeNumber <= 28) return 'text-2xl'
  if (sizeNumber <= 32) return 'text-3xl'
  return 'text-4xl'
})

const customStyle = computed(() => {
  const styles: any = {}
  if (props.color) {
    styles.color = props.color
  }
  if (typeof props.size === 'number' && props.size > 32) {
    styles.fontSize = `${props.size}px`
  }
  return styles
})
</script>

<style scoped>
/* 确保图标垂直对齐 */
i {
  display: inline-block;
  vertical-align: middle;
  line-height: 1;
}
</style>