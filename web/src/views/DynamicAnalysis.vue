<template>
  <div class="dynamic-analysis-view">
    <div class="view-header">
      <h1 class="view-title">{{ t('dynamicAnalysis.title') }}</h1>
      <p class="view-description">{{ t('dynamicAnalysis.description') }}</p>
    </div>

    <DynamicAnalysisPanel />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import DynamicAnalysisPanel from '@/components/analysis/DynamicAnalysisPanel.vue'

const { t } = useI18n()
</script>

<style scoped>
.dynamic-analysis-view {
  @apply h-full flex flex-col;
}

.view-header {
  @apply px-6 py-4 bg-[var(--color-surface)] border-b border-[var(--color-border)];
}

.view-title {
  @apply text-2xl font-bold text-[var(--color-text)];
}

.view-description {
  @apply text-[var(--color-text-secondary)] mt-1;
}
</style>