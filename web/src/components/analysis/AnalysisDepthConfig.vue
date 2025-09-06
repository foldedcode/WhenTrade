<template>
  <div v-if="marketConfig?.hasDepthConfig" class="form-group">
    <label class="block text-xs font-medium mb-1.5" style="color: var(--od-text-secondary)">
      {{ $t('analysis.analysisDepth') }}
    </label>
    
    <!-- 专业金融终端风格的深度控制器 - 紧凑版 -->
    <div class="depth-control--terminal" :key="`depth-control-${marketType}`">
      <!-- 深度级别选择器 -->
      <div class="depth-levels--terminal">
        <div
          v-for="(level, index) in depthLevels"
          :key="`${marketType}-level-${index}-${level.value}`"
          class="depth-level--terminal"
          :class="{ 
            'active': modelValue !== null && modelValue >= level.value,
            'disabled': disabled 
          }"
          @click="handleLevelClick(level.value)"
        >
          <div class="level-bar"></div>
          <span class="level-label">{{ level.label }}</span>
        </div>
      </div>
      
      <!-- 深度描述 -->
      <div class="depth-info--terminal">
        <span class="info-icon">ℹ</span>
        <span class="info-text">{{ currentDepthDescription }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { MarketType, MarketConfig } from '@/types/market'
import { marketConfigService } from '@/services/market-config.service'
import { useI18n } from 'vue-i18n'

interface Props {
  modelValue: number | null
  marketType: MarketType
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: number | null): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const { t } = useI18n()

const marketConfig = ref<MarketConfig | null>(null)

// 深度级别定义
const depthLevels = computed(() => {
  if (!marketConfig.value) return []
  const { min, max } = marketConfig.value.depthRange
  
  // 根据范围生成对应数量的级别
  const levels = []
  for (let i = min; i <= max; i++) {
    levels.push({
      value: i,
      label: `L${i}`
    })
  }
  return levels
})

// 滑块进度百分比
const sliderProgress = computed(() => {
  if (!marketConfig.value || props.modelValue === null) return 0
  const { min, max } = marketConfig.value.depthRange
  return ((props.modelValue - min) / (max - min)) * 100
})

// 当前深度描述
const currentDepthDescription = computed(() => {
  if (!marketConfig.value) return ''
  
  // 如果没有选择深度级别，显示提示信息
  if (props.modelValue === null) {
    return t('analysis.selectDepthHint')
  }
  
  const progress = sliderProgress.value
  
  if (progress < 20) return t('analysis.depthDescriptions.minimal')
  if (progress < 40) return t('analysis.depthDescriptions.basic')
  if (progress < 60) return t('analysis.depthDescriptions.standard')
  if (progress < 80) return t('analysis.depthDescriptions.comprehensive')
  return t('analysis.depthDescriptions.exhaustive')
})

// 处理级别点击 - 支持点击取消
const handleLevelClick = (value: number) => {
  if (props.disabled) return
  
  if (props.modelValue === value) {
    // 如果点击的是当前选中的值，则取消选择
    emit('update:modelValue', null)
  } else {
    // 否则选择新值
    emit('update:modelValue', value)
  }
}

// 更新深度值
const updateDepth = (event: Event) => {
  const value = parseInt((event.target as HTMLInputElement).value)
  emit('update:modelValue', value)
}

// 加载市场配置
const loadMarketConfig = async () => {
  if (!props.marketType) return
  
  try {
    marketConfig.value = await marketConfigService.getMarketConfig(props.marketType)
    
    // 不再自动设置默认值，让用户自己选择
    // 只有当值无效时才重置
    if (marketConfig.value && props.modelValue !== null) {
      const { min, max } = marketConfig.value.depthRange
      if (props.modelValue < min || props.modelValue > max) {
        // 重置为 null，让用户重新选择
        emit('update:modelValue', null)
      }
    }
  } catch (error) {
    console.error('Failed to load market config:', error)
  }
}

// 监听市场类型变化
watch(() => props.marketType, () => {
  loadMarketConfig()
}, { immediate: true })
</script>

<style scoped>
/* 专业金融终端风格 - 深度控制器容器（紧凑版） */
.depth-control--terminal {
  background: var(--od-background-alt);
  border: 1px solid var(--od-border);
  border-radius: 0.375rem;
  padding: 0.5rem;
  position: relative;
}

/* 深度级别指示器 - 更小尺寸 */
.depth-levels--terminal {
  display: flex;
  gap: 0.125rem;
  margin-bottom: 0.5rem;
  padding: 0.25rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 0.25rem;
}

.depth-level--terminal {
  flex: 1;
  text-align: center;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
}

.depth-level--terminal .level-bar {
  width: 100%;
  height: 1rem;
  background: var(--od-border);
  border-radius: 0.125rem;
  margin-bottom: 0.125rem;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.depth-level--terminal.active .level-bar {
  background: linear-gradient(to right, var(--od-primary), var(--od-primary-light));
  box-shadow: 0 0 4px rgba(78, 201, 176, 0.4);
}

.depth-level--terminal.active .level-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.15) 0%,
    transparent 50%,
    rgba(255, 255, 255, 0.1) 100%
  );
  animation: levelPulse 2s ease infinite;
}

@keyframes levelPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.depth-level--terminal .level-label {
  font-size: 0.5625rem;
  font-weight: 600;
  color: var(--od-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: color 0.2s ease;
}

.depth-level--terminal.active .level-label {
  color: var(--od-primary-light);
  text-shadow: 0 0 4px rgba(78, 201, 176, 0.3);
}

/* 深度信息提示 - 紧凑版 */
.depth-info--terminal {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  background: rgba(78, 201, 176, 0.05);
  border: 1px solid rgba(78, 201, 176, 0.2);
  border-radius: 0.25rem;
  font-size: 0.5625rem;
}

.info-icon {
  width: 0.75rem;
  height: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--od-primary);
  color: var(--od-background);
  border-radius: 50%;
  font-size: 0.5rem;
  font-weight: 700;
  flex-shrink: 0;
}

.info-text {
  color: var(--od-text-secondary);
  line-height: 1.2;
}

/* 禁用状态样式 */
.depth-control--terminal:has(.depth-level--terminal.disabled) {
  opacity: 0.5;
  pointer-events: none;
}

.depth-level--terminal.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* 禁用状态下非选中的级别 */
.depth-level--terminal.disabled:not(.active) .level-bar {
  background: var(--od-border) !important;
  box-shadow: none !important;
}

.depth-level--terminal.disabled:not(.active) .level-label {
  color: var(--od-text-muted) !important;
  text-shadow: none !important;
}

/* 禁用状态下选中的级别 - 保持可见但降低透明度 */
.depth-level--terminal.disabled.active .level-bar {
  background: linear-gradient(to right, var(--od-primary), var(--od-primary-light)) !important;
  box-shadow: 0 0 4px rgba(78, 201, 176, 0.2) !important;
  opacity: 0.7;
}

.depth-level--terminal.disabled.active .level-label {
  color: var(--od-primary-light) !important;
  text-shadow: 0 0 4px rgba(78, 201, 176, 0.2) !important;
  opacity: 0.8;
}
</style>