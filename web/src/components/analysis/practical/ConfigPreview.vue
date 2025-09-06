<template>
  <div class="config-preview">
    <div class="panel-header">
      <span class="header-title">{{ $t('analysis.config.title') }}</span>
    </div>
    
    <div class="config-content">
      <!-- 市场类型 -->
      <div class="config-item" :class="{ highlight: formData.marketType }">
        <span class="config-label">{{ $t('analysis.config.labels.marketType') }}</span>
        <span class="config-value">{{ getMarketTypeName(formData.marketType) }}</span>
      </div>
      
      <!-- 分析标的 -->
      <div class="config-item" :class="{ highlight: formData.symbol }">
        <span class="config-label">{{ $t('analysis.config.labels.analysisTarget') }}</span>
        <span class="config-value">{{ formData.symbol || $t('analysis.config.labels.notSet') }}</span>
      </div>
      
      <!-- LLM配置 -->
      <div class="config-section">
        <div class="section-title">{{ $t('analysis.config.aiTitle') }}</div>
        <div class="config-item">
          <span class="config-label">{{ $t('analysis.config.labels.provider') }}</span>
          <span class="config-value">{{ formData.llmProvider || $t('common.default') }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">{{ $t('analysis.config.labels.model') }}</span>
          <span class="config-value">{{ formData.llmModel || $t('common.default') }}</span>
        </div>
      </div>
      
      <!-- 分析深度 -->
      <div class="config-item" :class="{ highlight: formData.depth }">
        <span class="config-label">{{ $t('analysis.config.labels.analysisDepth') }}</span>
        <span class="config-value">
          <span v-if="formData.depth" class="depth-indicator">
            L{{ formData.depth }}
          </span>
          <span v-else>{{ $t('analysis.config.labels.notSet') }}</span>
        </span>
      </div>
      
      <!-- 时间范围 -->
      <div class="config-item">
        <span class="config-label">{{ $t('analysis.config.labels.timeRange') }}</span>
        <span class="config-value">{{ formData.timeRange || $t('analysis.timeRanges.1d') }}</span>
      </div>
      
      <!-- 分析范围 -->
      <div class="config-section">
        <div class="section-title">{{ $t('analysis.config.scopes') }}</div>
        <div class="scope-list">
          <div v-if="!formData.analysisScopes?.length" class="empty-scopes">
            {{ $t('analysis.config.labels.noScopesSelected') }}
          </div>
          <div 
            v-for="scope in formData.analysisScopes" 
            :key="scope"
            class="scope-item"
          >
            {{ getScopeName(scope) }}
          </div>
        </div>
      </div>
      
      <!-- 配置状态 -->
      <div class="config-status">
        <div v-if="isConfigComplete" class="status-ready">
          ✓ {{ $t('analysis.config.complete') }}
        </div>
        <div v-else class="status-incomplete">
          <div class="status-message">{{ $t('analysis.config.pending') }}:</div>
          <ul class="missing-items">
            <li v-if="!formData.symbol">{{ $t('analysis.config.checklist.selectTarget') }}</li>
            <li v-if="!formData.analysisScopes?.length">{{ $t('analysis.config.checklist.selectScopes') }}</li>
            <li v-if="!formData.depth">{{ $t('analysis.config.checklist.setDepth') }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Props {
  formData: {
    symbol?: string
    marketType?: string
    depth?: number | null
    llmModel?: string | null
    llmProvider?: string | null
    analysisScopes?: string[]
    timeRange?: string
  }
}

const props = defineProps<Props>()
const { t } = useI18n()

// 计算属性
const isConfigComplete = computed(() => {
  return !!(
    props.formData.symbol && 
    props.formData.analysisScopes?.length && 
    props.formData.depth
  )
})

// 辅助方法
const getMarketTypeName = (type?: string) => {
  if (!type) return t('analysis.config.labels.notSet')
  
  try {
    return t(`analysis.marketTypes.${type}`)
  } catch {
    return type
  }
}

const getScopeName = (scope: string) => {
  try {
    return t(`analysis.scopes.${scope}`)
  } catch {
    return scope
  }
}
</script>

<style lang="scss" scoped>
.config-preview {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: #00ff41;
  font-family: 'Proto Mono', monospace;
  font-size: 11px;
}

.panel-header {
  padding: 0.625rem 0.875rem;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
  
  .header-title {
    color: var(--od-primary-light);
    font-weight: bold;
    text-transform: uppercase;
    font-size: 12px;
  }
}

.config-content {
  flex: 1;
  padding: 0.875rem;
  overflow-y: auto;
  
  .config-item {
    display: flex;
    justify-content: space-between;
    padding: 0.625rem 0.75rem;
    margin-bottom: 0.375rem;
    border: 1px solid transparent;
    transition: all 0.2s;
    
    &.highlight {
      border-color: #333;
      background: rgba(0, 255, 65, 0.05);
    }
    
    .config-label {
      color: #888;
      flex-shrink: 0;
    }
    
    .config-value {
      color: #00ff41;
      text-align: right;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-left: 0.5rem;
      
      .depth-indicator {
        padding: 0.125rem 0.5rem;
        background: #333;
        border-radius: 3px;
        color: var(--od-primary-light);
        font-weight: bold;
      }
    }
  }
  
  .config-section {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #333;
    
    .section-title {
      color: var(--od-primary-light);
      font-weight: bold;
      margin-bottom: 0.5rem;
      text-transform: uppercase;
      font-size: 11px;
    }
  }
  
  .scope-list {
    .empty-scopes {
      color: #666;
      font-style: italic;
      padding: 0.5rem;
    }
    
    .scope-item {
      padding: 0.25rem 0.5rem;
      margin-bottom: 0.25rem;
      background: rgba(0, 255, 65, 0.1);
      border-left: 2px solid #00ff41;
      color: #00ff41;
    }
  }
  
  .config-status {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #333;
    
    .status-ready {
      color: #00ff41;
      text-align: center;
      padding: 0.5rem;
      background: rgba(0, 255, 65, 0.1);
      border: 1px solid #00ff41;
      border-radius: 3px;
    }
    
    .status-incomplete {
      .status-message {
        color: var(--od-primary-light);
        margin-bottom: 0.5rem;
      }
      
      .missing-items {
        list-style: none;
        margin: 0;
        padding: 0;
        
        li {
          color: #888;
          padding: 0.25rem 0;
        }
      }
    }
  }
}

// 滚动条样式
.config-content::-webkit-scrollbar {
  width: 6px;
}

.config-content::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.config-content::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
  
  &:hover {
    background: #444;
  }
}
</style>