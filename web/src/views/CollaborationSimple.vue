<template>
  <div class="collaboration-simple-page">
    <div class="page-header">
      <h1 class="page-title">智能体协作演示（简化版）</h1>
      <p class="page-subtitle">
        使用原始的AgentCollaboration组件展示协作分析
      </p>
    </div>

    <div class="demo-controls">
      <select v-model="selectedSymbol" class="symbol-select">
        <option value="AAPL">苹果 (AAPL)</option>
        <option value="GOOGL">谷歌 (GOOGL)</option>
        <option value="BTC">比特币 (BTC)</option>
        <option value="ETH">以太坊 (ETH)</option>
      </select>
      <button @click="startAnalysis" class="btn-primary">
        <i class="fas fa-play"></i>
        开始分析
      </button>
      <button @click="refreshAnalysis" class="btn-secondary">
        <i class="fas fa-sync"></i>
        刷新分析
      </button>
    </div>

    <!-- 原始协作组件 -->
    <AgentCollaboration
      :task-id="taskId"
      :symbol="selectedSymbol"
      class="collaboration-component"
    />

    <!-- 组件状态信息 -->
    <div class="status-info">
      <p>任务ID: {{ taskId }}</p>
      <p>选中标的: {{ selectedSymbol }}</p>
      <p>刷新时间: {{ lastRefresh }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AgentCollaboration from '@/components/analysis/AgentCollaboration.vue'

// 状态管理
const taskId = ref(`task_${Date.now()}`)
const selectedSymbol = ref('AAPL')
const lastRefresh = ref(new Date().toLocaleTimeString())

// 方法
const startAnalysis = () => {
  taskId.value = `task_${Date.now()}`
  lastRefresh.value = new Date().toLocaleTimeString()
  // 这会触发 AgentCollaboration 组件重新初始化并开始分析
}

const refreshAnalysis = () => {
  taskId.value = `task_${Date.now()}`
  lastRefresh.value = new Date().toLocaleTimeString()
}
</script>

<style scoped>
.collaboration-simple-page {
  @apply min-h-screen bg-[var(--color-background)] p-6;
}

.page-header {
  @apply text-center mb-8;
}

.page-title {
  @apply text-3xl font-bold text-[var(--color-text)] mb-2;
}

.page-subtitle {
  @apply text-[var(--color-text-secondary)];
}

.demo-controls {
  @apply flex justify-center items-center gap-4 mb-8;
}

.symbol-select {
  @apply px-4 py-3 bg-[var(--color-surface)] border border-[var(--color-border)]
         rounded-lg text-[var(--color-text)];
}

.btn-primary {
  @apply flex items-center gap-2 px-6 py-3 bg-[var(--color-primary)] text-white 
         rounded-lg hover:bg-[var(--color-primary-hover)] transition-colors;
}

.btn-secondary {
  @apply flex items-center gap-2 px-6 py-3 bg-[var(--color-surface)] 
         border border-[var(--color-border)] text-[var(--color-text)]
         rounded-lg hover:bg-[var(--color-hover)] transition-colors;
}

.collaboration-component {
  @apply mb-8;
}

.status-info {
  @apply text-center space-y-2 text-sm text-[var(--color-text-secondary)];
}
</style>