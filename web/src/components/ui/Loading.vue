<template>
  <div class="flex flex-col items-center justify-center" :class="containerClass">
    <!-- 加载动画 -->
    <div class="relative">
      <div v-if="type === 'spinner'" class="animate-spin rounded-full border-2 border-slate-600/50 border-t-blue-500" :class="sizeClass"></div>
      
      <div v-else-if="type === 'dots'" class="flex space-x-1">
        <div v-for="i in 3" :key="i" class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" :style="{ animationDelay: `${i * 0.1}s` }"></div>
      </div>
      
      <div v-else-if="type === 'pulse'" class="rounded-full bg-blue-500 animate-pulse" :class="sizeClass"></div>
      
      <div v-else-if="type === 'bars'" class="flex space-x-1">
        <div v-for="i in 4" :key="i" class="w-1 bg-blue-500 rounded-full animate-pulse" :class="barHeightClass" :style="{ animationDelay: `${i * 0.1}s` }"></div>
      </div>
    </div>
    
    <!-- 加载文本 -->
    <div v-if="text" class="mt-2 text-center">
      <p class="text-base text-slate-300 font-medium" :class="textSizeClass">{{ text }}</p>
      <p v-if="description" class="text-sm text-slate-400 mt-1" :class="descriptionSizeClass">{{ description }}</p>
    </div>
    
    <!-- 进度条 -->
    <div v-if="showProgress && progress >= 0" class="mt-2 w-full max-w-xs">
      <div class="flex justify-between text-sm text-slate-400 mb-1">
        <span>{{ $t('common.progress') }}</span>
        <span>{{ Math.round(progress) }}%</span>
      </div>
      <div class="w-full bg-slate-700/50 rounded-lg h-2 overflow-hidden">
        <div 
          class="bg-blue-500 h-full rounded-lg transition-all duration-300 ease-out"
          :style="{ width: `${Math.min(100, Math.max(0, progress))}%` }"
        ></div>
      </div>
    </div>
    
    <!-- 取消按钮 -->
    <button
      v-if="showCancel"
      @click="$emit('cancel')"
      class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500 transition-colors mt-2"
    >
      {{ $t('common.cancel') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  type?: 'spinner' | 'dots' | 'pulse' | 'bars'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  text?: string
  description?: string
  progress?: number
  showProgress?: boolean
  showCancel?: boolean
  fullScreen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'spinner',
  size: 'md',
  text: '',
  description: '',
  progress: -1,
  showProgress: false,
  showCancel: false,
  fullScreen: false
})

const emit = defineEmits<{
  cancel: []
}>()

const { t } = useI18n()

const containerClass = computed(() => {
  const classes = ['loading-container']
  
  if (props.fullScreen) {
    classes.push('fixed inset-0 bg-slate-900/80 backdrop-blur-sm z-50')
  }
  
  return classes.join(' ')
})

const sizeClass = computed(() => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  }
  return sizes[props.size]
})

const textSizeClass = computed(() => {
  const sizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl'
  }
  return sizes[props.size]
})

const descriptionSizeClass = computed(() => {
  const sizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
    xl: 'text-lg'
  }
  return sizes[props.size]
})

const barHeightClass = computed(() => {
  const heights = {
    sm: 'h-4',
    md: 'h-6',
    lg: 'h-8',
    xl: 'h-10'
  }
  return heights[props.size]
})
</script>

<style scoped>
@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.animate-bounce {
  animation: bounce 1.4s infinite ease-in-out both;
}

@keyframes pulse-bars {
  0%, 40%, 100% {
    transform: scaleY(0.4);
  }
  20% {
    transform: scaleY(1);
  }
}

.animate-pulse {
  animation: pulse-bars 1.2s infinite ease-in-out;
}
</style> 