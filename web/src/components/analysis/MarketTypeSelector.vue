<template>
  <div class="form-group">
    <label class="block text-xs font-medium mb-1" style="color: var(--od-text-secondary)">
      {{ $t('analysis.marketType') }}
    </label>
    <div class="grid grid-cols-2 gap-2">
      <button
        v-for="market in availableMarkets"
        :key="market.id"
        :class="[
          'market-type-button--od',
          modelValue === market.id ? 'market-type-button--od--active' : '',
          disabled ? 'market-type-button--od--disabled' : ''
        ]"
        :disabled="disabled"
        @click="selectMarket(market.id)"
      >
        <span class="market-icon--od">{{ market.icon }}</span>
        <span class="market-name--od">{{ $t(market.name) }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import type { MarketType, MarketConfig } from '@/types/market'
import { marketConfigService } from '@/services/market-config.service'

interface Props {
  modelValue: MarketType
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: MarketType): void
  (e: 'change', value: MarketType, config: MarketConfig): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const availableMarkets = ref<MarketConfig[]>([])

// 加载可用市场
const loadAvailableMarkets = async () => {
  try {
    const marketTypes = await marketConfigService.getAvailableMarkets()
    const configs = await marketConfigService.getMarketConfigs(marketTypes)
    
    availableMarkets.value = Array.from(configs.values())
  } catch (error) {
    console.error('Failed to load available markets:', error)
  }
}

// 选择市场
const selectMarket = async (marketType: MarketType) => {
  if (props.disabled || marketType === props.modelValue) return
  
  emit('update:modelValue', marketType)
  
  // 获取市场配置并触发 change 事件
  const config = await marketConfigService.getMarketConfig(marketType)
  if (config) {
    emit('change', marketType, config)
  }
}

// 初始化时加载市场
onMounted(() => {
  loadAvailableMarkets()
})

// 监听外部值变化
watch(() => props.modelValue, async (newValue) => {
  if (newValue) {
    const config = await marketConfigService.getMarketConfig(newValue)
    if (config) {
      emit('change', newValue, config)
    }
  }
})
</script>

<style scoped>
/* 市场类型按钮 - 与 card--od 风格一致 */
.market-type-button--od {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid var(--od-border);
  background: var(--od-bg-card);
  color: var(--od-text-primary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.market-type-button--od:hover {
  background: var(--od-bg-hover);
  border-color: var(--od-border-hover);
  transform: translateY(-1px);
}

.market-type-button--od--active {
  background: var(--od-bg-accent);
  border-color: var(--od-color-primary);
  color: var(--od-color-primary);
  box-shadow: 0 0 0 1px var(--od-color-primary-20);
}

.market-type-button--od--active:hover {
  background: var(--od-bg-accent-hover);
}

.market-icon--od {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
  line-height: 1;
}

.market-name--od {
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1;
}

/* 禁用状态样式 */
.market-type-button--od--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.market-type-button--od--disabled:hover {
  transform: none;
  background: var(--od-bg-card);
  border-color: var(--od-border);
}
</style>