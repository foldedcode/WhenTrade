<template>
  <div 
    class="scope-card" 
    :class="{ active: isSelected, configured: isSelected && isConfigured }"
  >
    <span class="card-title">{{ $t(scope.name) }}</span>
    
    <!-- 未选择该分析范围 -->
    <div v-if="!isSelected && !isConfigured" class="card-status">
      <span class="empty-text">{{ $t('analysis.config.unselected') }}</span>
    </div>
    <!-- 未选择但有配置 - 显示灰色的配置信息 -->
    <div v-else-if="!isSelected && isConfigured" class="card-status inactive-configured">
      <span v-if="selectedTools.length" class="status-item">{{ $t('analysis.config.tools') }}:{{ selectedTools.length }}</span>
      <span v-if="selectedDataSources.length" class="status-item">{{ $t('analysis.config.data') }}:{{ selectedDataSources.length }}</span>
    </div>
    <!-- 已选择但未配置 - 显示未配置状态 -->
    <div v-else-if="isSelected && !isConfigured" class="card-status default-status">
      <span class="unconfigured-text">{{ $t('analysis.config.unconfigured') }}</span>
    </div>
    <!-- 已选择且已配置 -->
    <div v-else-if="isSelected && isConfigured" class="card-status configured-status">
      <span v-if="selectedTools.length" class="status-item">{{ $t('analysis.config.tools') }}:{{ selectedTools.length }}</span>
      <span v-if="selectedDataSources.length" class="status-item">{{ $t('analysis.config.data') }}:{{ selectedDataSources.length }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

// 显式定义组件名称以提高 Vetur 兼容性
defineOptions({
  name: 'AnalysisScopeCard'
})

interface Tool {
  id: string
  name: string
}

interface ScopeConfig {
  id: string
  name: string
  availableTools: Tool[]
  availableDataSources: Tool[]
}

interface Props {
  scope: ScopeConfig
  modelValue: boolean
  config?: {
    tools?: string[]
    dataSources?: string[]
  }
  symbol?: string  // 当前选择的标的
  disabled?: boolean  // 添加禁用属性
}

const props = defineProps<Props>()

// 选中的配置 - 监听 props.config 变化并更新
const selectedTools = ref<string[]>(props.config?.tools || [])
const selectedDataSources = ref<string[]>(props.config?.dataSources || [])

// 监听配置变化
watch(() => props.config, (newConfig) => {
  if (newConfig) {
    selectedTools.value = newConfig.tools || []
    selectedDataSources.value = newConfig.dataSources || []
  }
}, { deep: true, immediate: true })

// 计算属性
const isSelected = computed(() => props.modelValue)

const isConfigured = computed(() => {
  return selectedTools.value.length > 0 || 
         selectedDataSources.value.length > 0
})

</script>

<style lang="scss" scoped>
.scope-card {
  width: 100%;
  background: var(--od-background);
  border: 1px solid var(--od-border);
  border-radius: var(--border-radius-sm);
  padding: 0.3rem 0.5rem;
  transition: all 0.2s;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.2rem;
  min-height: 28px;
  
  &.active {
    border-color: var(--od-border);
    background: var(--od-background);
    position: relative;
    
    .card-title {
      color: var(--od-primary-light);
      font-weight: 600;
      text-shadow: 0 0 15px rgba(74, 222, 128, 0.6);
    }
  }
  
  &.configured:not(.active) {
    .card-title {
      color: var(--od-text-secondary);
    }
  }
  
  .card-title {
    font-size: 11px;
    font-weight: bold;
    color: var(--od-text-secondary);
    flex-shrink: 0;
    transition: all 0.2s;
    white-space: nowrap;
  }
  
  .card-status {
    font-size: 10px;
    color: var(--od-text-secondary);
    display: flex;
    align-items: center;
    gap: 0.15rem;
    justify-content: flex-end;
    flex-shrink: 1;
    overflow: hidden;
    
    .empty-text {
      color: var(--od-text-muted);
    }
    
    .unconfigured-text {
      color: var(--od-accent);
      text-shadow: 0 0 10px rgba(255, 183, 77, 0.5);
    }
    
    &.configured-status {
      color: var(--od-primary-light);
      
      .status-item {
        background: transparent;
        padding: 0.05rem 0.15rem;
        border-radius: 2px;
        border: 1px solid rgba(74, 222, 128, 0.3);
        color: var(--od-primary-light);
        font-weight: 500;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.2px;
        transition: all 0.2s ease;
        white-space: nowrap;
        text-shadow: 0 0 10px rgba(74, 222, 128, 0.8);
        
        &:hover {
          background: rgba(74, 222, 128, 0.05);
          border-color: rgba(74, 222, 128, 0.5);
        }
      }
    }
    
    &.default-status {
      color: var(--od-accent);
      
      .status-item {
        background: transparent;
        padding: 0.05rem 0.15rem;
        border-radius: 2px;
        border: 1px solid rgba(255, 183, 77, 0.2);
        color: var(--od-accent);
        font-weight: 400;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.2px;
        transition: all 0.2s ease;
        white-space: nowrap;
        opacity: 0.8;
        
        &:hover {
          background: rgba(255, 183, 77, 0.05);
          border-color: rgba(255, 183, 77, 0.3);
          opacity: 1;
        }
      }
    }
    
    &.inactive-configured {
      color: var(--od-text-muted);
      
      .status-item {
        background: transparent;
        padding: 0.05rem 0.15rem;
        border-radius: 2px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: var(--od-text-muted);
        font-weight: 400;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: 0.2px;
        opacity: 0.5;
      }
    }
  }
  
}

</style>