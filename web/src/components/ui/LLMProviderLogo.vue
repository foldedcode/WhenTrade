<template>
  <div 
    :class="[
      'llm-provider-logo',
      sizeClass,
      { 'logo-loading': isLoading, 'logo-error': hasError }
    ]"
    :style="containerStyle"
  >
    <!-- 主Logo图片 -->
    <img 
      v-if="!hasError"
      :src="logoPath" 
      :alt="altText"
      :title="title"
      class="provider-logo"
      @load="handleImageLoad"
      @error="handleImageError"
      :loading="lazy ? 'lazy' : 'eager'"
    />
    
    <!-- 错误回退显示 -->
    <div v-else class="logo-fallback">
      <div class="fallback-icon">
        <component :is="fallbackIcon" />
      </div>
      <span v-if="showFallbackText" class="fallback-text">
        {{ fallbackText }}
      </span>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="logo-loading-overlay">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTheme } from '@/composables/useTheme'
import { resolveLogoPath, type LogoResolveOptions } from '@/config/logoProviders'

// Props定义
interface Props {
  /** LLM提供商名称 */
  provider: string
  /** Logo尺寸 */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'custom'
  /** 自定义尺寸（当size为custom时使用） */
  customSize?: string
  /** 是否懒加载 */
  lazy?: boolean
  /** 是否显示回退文本 */
  showFallbackText?: boolean
  /** 自定义alt文本 */
  alt?: string
  /** 自定义title文本 */
  title?: string
  /** 强制使用特定主题的logo */
  forceTheme?: 'light' | 'dark'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  lazy: true,
  showFallbackText: true
})

// 使用主题管理
const { getCurrentTheme } = useTheme()

// 组件状态
const isLoading = ref(true)
const hasError = ref(false)

// Logo解析结果
const logoResult = ref<ReturnType<typeof resolveLogoPath> | null>(null)

// 解析Logo信息
const resolveLogo = () => {
  const options: LogoResolveOptions = {
    theme: props.forceTheme || (getCurrentTheme.value.isDark ? 'dark' : 'light'),
    preferColor: false, // 默认使用黑白图标
    enableFallback: true
  }
  
  logoResult.value = resolveLogoPath(props.provider, options)
}

// 计算Logo路径
const logoPath = computed(() => logoResult.value?.path || null)

// 计算尺寸类名
const sizeClass = computed(() => {
  if (props.size === 'custom') {
    return 'logo-custom'
  }
  return `logo-${props.size}`
})

// 计算容器样式
const containerStyle = computed(() => {
  if (props.size === 'custom' && props.customSize) {
    return {
      width: props.customSize,
      height: props.customSize
    }
  }
  return {}
})

// 计算alt文本
const altText = computed(() => {
  if (props.alt) {
    return props.alt
  }
  
  const config = logoResult.value?.config
  return config ? `${config.name} Logo` : `${props.provider} Logo`
})

// 计算title文本
const title = computed(() => {
  if (props.title) {
    return props.title
  }
  
  const config = logoResult.value?.config
  return config ? config.name : props.provider
})

// 计算回退文本
const fallbackText = computed(() => {
  const config = logoResult.value?.config
  return config ? config.name : props.provider
})

// 回退图标组件 - 使用渲染函数代替模板
import { h } from 'vue'

const fallbackIcon = {
  render() {
    return h('svg', {
      viewBox: '0 0 24 24',
      fill: 'currentColor',
      class: 'w-full h-full'
    }, [
      h('path', {
        d: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z'
      })
    ])
  }
}

// 事件处理
const handleImageLoad = () => {
  isLoading.value = false
  hasError.value = false
}

const handleImageError = () => {
  isLoading.value = false
  hasError.value = true
  
  // 发出错误事件，便于父组件处理
  emit('error', {
    provider: props.provider,
    path: logoPath.value
  })
}

// 初始化Logo解析
resolveLogo()

// 监听provider变化，重新解析Logo
watch(() => props.provider, () => {
  resolveLogo()
  isLoading.value = true
  hasError.value = false
})

// 监听主题变化，重新解析Logo
watch(() => getCurrentTheme.value.isDark, () => {
  if (!props.forceTheme) {
    resolveLogo()
    isLoading.value = true
    hasError.value = false
  }
})

// 事件定义
const emit = defineEmits<{
  error: [{ provider: string; path: string | null }]
  load: [{ provider: string; path: string | null }]
}>()

// 暴露给父组件的方法
defineExpose({
  reload: () => {
    isLoading.value = true
    hasError.value = false
  },
  hasError: () => hasError.value,
  isLoading: () => isLoading.value
})
</script>

<style scoped>
/* 基础容器样式 */
.llm-provider-logo {
  @apply relative inline-flex items-center justify-center;
  @apply transition-all duration-200;
}

/* 尺寸系统 */
.logo-xs {
  @apply w-4 h-4;
}

.logo-sm {
  @apply w-6 h-6;
}

.logo-md {
  @apply w-8 h-8;
}

.logo-lg {
  @apply w-12 h-12;
}

.logo-xl {
  @apply w-16 h-16;
}

.logo-custom {
  /* 自定义尺寸通过内联样式设置 */
}

/* Logo图片样式 */
.provider-logo {
  @apply w-full h-full object-contain;
  @apply transition-opacity duration-200;
}

/* 加载状态 */
.logo-loading .provider-logo {
  @apply opacity-50;
}

.logo-loading-overlay {
  @apply absolute inset-0 flex items-center justify-center;
  @apply bg-slate-800/50 rounded;
}

.loading-spinner {
  @apply w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full;
  @apply animate-spin;
}

/* 错误回退样式 */
.logo-fallback {
  @apply flex flex-col items-center justify-center;
  @apply w-full h-full p-1;
  @apply bg-slate-700 rounded border border-slate-600;
  @apply text-slate-300;
}

.fallback-icon {
  @apply w-1/2 h-1/2 mb-1;
  @apply text-slate-400;
}

.fallback-text {
  @apply text-xs font-medium text-center leading-tight;
  @apply truncate w-full;
}

/* 不同尺寸的回退文本调整 */
.logo-xs .fallback-text,
.logo-sm .fallback-text {
  @apply hidden;
}

.logo-md .fallback-text {
  @apply text-xs;
}

.logo-lg .fallback-text {
  @apply text-sm;
}

.logo-xl .fallback-text {
  @apply text-base;
}

/* 悬停效果 */
.llm-provider-logo:hover {
  @apply scale-105;
}

.llm-provider-logo:hover .provider-logo {
  @apply opacity-90;
}

/* 错误状态 */
.logo-error {
  @apply opacity-75;
}

/* 响应式调整 */
@media (max-width: 640px) {
  .logo-lg {
    @apply w-10 h-10;
  }
  
  .logo-xl {
    @apply w-12 h-12;
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .logo-fallback {
    @apply border-2 border-slate-500;
  }
}

/* 减少动画模式支持 */
@media (prefers-reduced-motion: reduce) {
  .llm-provider-logo,
  .provider-logo,
  .loading-spinner {
    @apply transition-none;
  }
  
  .llm-provider-logo:hover {
    @apply scale-100;
  }
  
  .loading-spinner {
    @apply animate-none;
  }
}

/* 打印样式 */
@media print {
  .logo-loading-overlay {
    @apply hidden;
  }
  
  .logo-fallback {
    @apply border border-black;
  }
}
</style>