<template>
  <div class="llm-config">
    <div class="config-header">
      <h3>LLM 配置</h3>
      <button @click="showSettings = !showSettings" class="toggle-btn">
        {{ showSettings ? '▼' : '▶' }}
      </button>
    </div>
    
    <div v-if="showSettings" class="config-content">
      <!-- LLM启用开关 -->
      <div class="config-item">
        <label class="switch">
          <input type="checkbox" v-model="useLLM" @change="updateLLMUsage">
          <span class="slider"></span>
        </label>
        <span class="label">{{ useLLM ? '使用真实LLM' : '使用模拟数据' }}</span>
      </div>
      
      <!-- LLM提供商选择 -->
      <div v-if="useLLM" class="config-item">
        <label class="label">提供商：</label>
        <select v-model="selectedProvider" @change="onProviderChange" class="select">
          <option value="">选择提供商</option>
          <option v-for="provider in availableProviders" :key="provider.id" :value="provider.id">
            {{ provider.name }}
          </option>
        </select>
      </div>
      
      <!-- 模型选择 -->
      <div v-if="useLLM && selectedProvider" class="config-item">
        <label class="label">模型：</label>
        <select v-model="selectedModel" @change="onModelChange" class="select">
          <option value="">选择模型</option>
          <option v-for="model in availableModels" :key="model.id" :value="model.id">
            {{ model.name }}
          </option>
        </select>
      </div>
      
      <!-- 模型详情 -->
      <div v-if="currentModel" class="model-details">
        <div class="detail-item">
          <span class="detail-label">描述：</span>
          <span class="detail-value">{{ currentModel.description }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">上下文窗口：</span>
          <span class="detail-value">{{ formatContextWindow(currentModel.contextWindow) }}</span>
        </div>
        <div v-if="currentModel.pricing" class="detail-item">
          <span class="detail-label">价格：</span>
          <span class="detail-value">
            输入 ${{ currentModel.pricing.input }}/1K | 输出 ${{ currentModel.pricing.output }}/1K
          </span>
        </div>
      </div>
      
      <!-- 高级设置 -->
      <div v-if="useLLM && selectedModel" class="advanced-settings">
        <h4>高级设置</h4>
        
        <div class="config-item">
          <label class="label">温度 (Temperature)：</label>
          <input 
            type="range" 
            v-model.number="temperature" 
            min="0" 
            max="1" 
            step="0.1"
            class="slider-input"
          >
          <span class="value">{{ temperature }}</span>
        </div>
        
        <div class="config-item">
          <label class="label">最大Token数：</label>
          <input 
            type="number" 
            v-model.number="maxTokens" 
            min="50" 
            max="2000" 
            step="50"
            class="number-input"
          >
        </div>
        
        <div class="config-item">
          <label class="switch">
            <input type="checkbox" v-model="stream">
            <span class="slider"></span>
          </label>
          <span class="label">流式输出</span>
        </div>
      </div>
      
      <!-- 保存按钮 -->
      <div class="config-actions">
        <button @click="saveConfig" :disabled="!canSave" class="save-btn">
          保存配置
        </button>
        <button @click="resetConfig" class="reset-btn">
          重置默认
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { llmDetectionService, type LLMProvider, type LLMModel } from '@/services/llm-detection.service'

const emit = defineEmits<{
  'config-change': [config: {
    provider: string
    model: string
    temperature: number
    maxTokens: number
    stream: boolean
  }]
}>()

// 状态
const showSettings = ref(false)
const useLLM = ref(true)  // 默认启用LLM，后续根据后端状态调整
const selectedProvider = ref('')
const selectedModel = ref('')
const temperature = ref(0.7)
const maxTokens = ref(500)
const stream = ref(true)

// 可用的提供商和模型
const availableProviders = ref<LLMProvider[]>([])
const availableModels = ref<LLMModel[]>([])

// 计算属性
const currentModel = computed(() => {
  return availableModels.value.find(m => m.id === selectedModel.value)
})

const canSave = computed(() => {
  if (!useLLM.value) return true
  return selectedProvider.value && selectedModel.value
})

// 方法
const updateLLMUsage = () => {
  localStorage.setItem('useLLM', useLLM.value.toString())
  emitConfigChange()
}

const onProviderChange = async () => {
  selectedModel.value = ''
  if (selectedProvider.value) {
    const models = await llmDetectionService.getModelsForProvider(selectedProvider.value)
    availableModels.value = models
    
    // 自动选择推荐的模型
    const recommendedModel = models.find(m => m.recommended)
    if (recommendedModel) {
      selectedModel.value = recommendedModel.id
    }
  } else {
    availableModels.value = []
  }
  emitConfigChange()
}

const onModelChange = () => {
  emitConfigChange()
}

const saveConfig = () => {
  // 保存到localStorage
  localStorage.setItem('llmProvider', selectedProvider.value)
  localStorage.setItem('llmModel', selectedModel.value)
  localStorage.setItem('llmTemperature', temperature.value.toString())
  localStorage.setItem('llmMaxTokens', maxTokens.value.toString())
  localStorage.setItem('llmStream', stream.value.toString())
  
  emitConfigChange()
  console.log('✅ LLM配置已保存')
}

const resetConfig = async () => {
  // 获取推荐配置
  const recommended = await llmDetectionService.getRecommendedConfig()
  if (recommended) {
    selectedProvider.value = recommended.providerId
    await onProviderChange()
    selectedModel.value = recommended.modelId
  }
  
  temperature.value = 0.7
  maxTokens.value = 500
  stream.value = true
  
  saveConfig()
}

const emitConfigChange = () => {
  emit('config-change', {
    provider: selectedProvider.value,
    model: selectedModel.value,
    temperature: temperature.value,
    maxTokens: maxTokens.value,
    stream: stream.value
  })
}

const formatContextWindow = (tokens: number): string => {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`
  } else if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(0)}K`
  }
  return tokens.toString()
}

// 初始化
onMounted(async () => {
  // 检测可用的LLM提供商
  await llmDetectionService.initialize()
  availableProviders.value = await llmDetectionService.getAvailableProviders()
  
  // 智能设置LLM开关：如果有可用提供商则启用，否则禁用
  const hasAvailableProviders = availableProviders.value.length > 0
  
  // 从localStorage恢复配置，但优先考虑后端可用性
  const savedUseLLM = localStorage.getItem('useLLM')
  if (savedUseLLM !== null) {
    // 用户曾经手动设置过，尊重用户选择（但仍需要有可用提供商）
    useLLM.value = savedUseLLM !== 'false' && hasAvailableProviders
  } else {
    // 首次使用，根据后端可用性自动设置
    useLLM.value = hasAvailableProviders
  }
  
  selectedProvider.value = localStorage.getItem('llmProvider') || ''
  selectedModel.value = localStorage.getItem('llmModel') || ''
  temperature.value = parseFloat(localStorage.getItem('llmTemperature') || '0.7')
  maxTokens.value = parseInt(localStorage.getItem('llmMaxTokens') || '500')
  stream.value = localStorage.getItem('llmStream') !== 'false'
  
  // 如果有选中的提供商，加载其模型
  if (selectedProvider.value) {
    const models = await llmDetectionService.getModelsForProvider(selectedProvider.value)
    availableModels.value = models
  }
  
  // 如果没有配置但有可用提供商，使用推荐配置
  if (!selectedProvider.value && hasAvailableProviders) {
    const recommended = await llmDetectionService.getRecommendedConfig()
    if (recommended) {
      selectedProvider.value = recommended.providerId
      await onProviderChange()
      selectedModel.value = recommended.modelId
      
      // 自动保存推荐配置
      saveConfig()
    }
  }
  
  // 如果没有可用提供商，禁用LLM并给出提示
  if (!hasAvailableProviders) {
    useLLM.value = false
    console.warn('⚠️ 没有检测到可用的LLM提供商，已自动禁用LLM功能')
  }
  
  // 更新localStorage以反映当前状态
  localStorage.setItem('useLLM', useLLM.value.toString())
})
</script>

<style lang="scss" scoped>
.llm-config {
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
  border-radius: var(--border-radius-sm);
  padding: 0.75rem;
  margin-bottom: 1rem;
  
  .config-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    
    h3 {
      margin: 0;
      font-size: 14px;
      color: var(--od-text-primary);
    }
    
    .toggle-btn {
      background: none;
      border: none;
      color: var(--od-text-secondary);
      cursor: pointer;
      padding: 0.25rem;
      font-size: 12px;
      
      &:hover {
        color: var(--od-primary);
      }
    }
  }
  
  .config-content {
    .config-item {
      display: flex;
      align-items: center;
      margin-bottom: 0.75rem;
      
      .label {
        color: var(--od-text-secondary);
        font-size: 13px;
        margin-left: 0.5rem;
      }
      
      .select {
        flex: 1;
        padding: 0.25rem 0.5rem;
        background: var(--od-background);
        border: 1px solid var(--od-border);
        border-radius: 4px;
        color: var(--od-text-primary);
        font-size: 13px;
        
        &:focus {
          outline: none;
          border-color: var(--od-primary);
        }
      }
      
      .slider-input {
        flex: 1;
        margin: 0 0.5rem;
      }
      
      .number-input {
        width: 80px;
        padding: 0.25rem 0.5rem;
        background: var(--od-background);
        border: 1px solid var(--od-border);
        border-radius: 4px;
        color: var(--od-text-primary);
        font-size: 13px;
        
        &:focus {
          outline: none;
          border-color: var(--od-primary);
        }
      }
      
      .value {
        color: var(--od-primary);
        font-size: 13px;
        font-weight: bold;
        min-width: 30px;
      }
    }
    
    .model-details {
      background: var(--od-background);
      padding: 0.5rem;
      border-radius: 4px;
      margin-bottom: 0.75rem;
      
      .detail-item {
        display: flex;
        margin-bottom: 0.25rem;
        font-size: 12px;
        
        .detail-label {
          color: var(--od-text-secondary);
          margin-right: 0.5rem;
        }
        
        .detail-value {
          color: var(--od-text-primary);
          flex: 1;
        }
      }
    }
    
    .advanced-settings {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid var(--od-border);
      
      h4 {
        margin: 0 0 0.75rem 0;
        font-size: 13px;
        color: var(--od-text-primary);
      }
    }
    
    .config-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 1rem;
      
      button {
        flex: 1;
        padding: 0.375rem 0.75rem;
        border-radius: 4px;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.2s;
        
        &.save-btn {
          background: var(--od-primary);
          color: var(--od-background);
          border: 1px solid var(--od-primary);
          
          &:hover:not(:disabled) {
            background: var(--od-primary-light);
          }
          
          &:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }
        }
        
        &.reset-btn {
          background: var(--od-background);
          color: var(--od-text-secondary);
          border: 1px solid var(--od-border);
          
          &:hover {
            background: var(--od-background-alt);
            color: var(--od-text-primary);
          }
        }
      }
    }
  }
  
  // Switch样式
  .switch {
    position: relative;
    display: inline-block;
    width: 36px;
    height: 20px;
    
    input {
      opacity: 0;
      width: 0;
      height: 0;
      
      &:checked + .slider {
        background-color: var(--od-primary);
        
        &:before {
          transform: translateX(16px);
        }
      }
    }
    
    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: var(--od-border);
      transition: 0.3s;
      border-radius: 20px;
      
      &:before {
        position: absolute;
        content: "";
        height: 14px;
        width: 14px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: 0.3s;
        border-radius: 50%;
      }
    }
  }
}
</style>