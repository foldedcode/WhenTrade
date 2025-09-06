<template>
  <div class="flex flex-col items-center justify-center py-12 px-4 text-center min-h-[300px]">
    <div class="empty-state-icon">
      <div class="terminal-icon-wrapper">
        {{ icon }}
      </div>
    </div>
    <h3 class="text-lg font-bold text-white">{{ title }}</h3>
    <p class="text-sm text-neutral-400 mt-2">
      {{ description }}
    </p>
    <button 
      v-if="actionText" 
      @click="$emit('action')"
      class="mt-4 px-4 py-2 bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors"
    >
      {{ actionText }}
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  icon?: string
  title: string
  description?: string
  actionText?: string
}

withDefaults(defineProps<Props>(), {
  icon: '📭',
  description: ''
})

defineEmits<{
  action: []
}>()
</script>

<style scoped>
.empty-state-icon {
  @apply mb-4;
}

.terminal-icon-wrapper {
  @apply w-20 h-20 flex items-center justify-center rounded-xl;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05));
  border: 2px solid rgba(59, 130, 246, 0.3);
  font-size: 2.5rem;
  position: relative;
  overflow: hidden;
}

.terminal-icon-wrapper::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(45deg, transparent, rgba(59, 130, 246, 0.1), transparent);
  animation: terminal-shimmer 3s infinite;
}

.terminal-icon-wrapper::after {
  content: '';
  position: absolute;
  inset: -50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%);
  opacity: 0;
  animation: pulse-glow 2s infinite;
}

@keyframes terminal-shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes pulse-glow {
  0%, 100% {
    opacity: 0;
    transform: scale(0.5);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}
</style>