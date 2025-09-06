<template>
  <div class="dynamic-domain-selector">
    <div class="selector-header">
      <h3 class="selector-title">{{ t('analysis.selectDomains') }}</h3>
      <div class="market-type-selector">
        <label class="market-label">{{ t('analysis.marketType') }}</label>
        <select v-model="selectedMarketType" @change="onMarketTypeChange" class="market-select">
          <option value="crypto">{{ t('analysis.marketTypes.crypto') }}</option>
        </select>
      </div>
    </div>

    <div class="domains-grid">
      <div v-for="domain in availableDomains" :key="domain.id" class="domain-card"
           :class="{ 'selected': isSelected(domain.id), 'recommended': isRecommended(domain.id) }"
           @click="toggleDomain(domain.id)">
        <div class="domain-icon">
          <i :class="getDomainIcon(domain.id)"></i>
        </div>
        <div class="domain-info">
          <h4 class="domain-name">{{ domain.name }}</h4>
          <p class="domain-description">{{ domain.description }}</p>
        </div>
        <div v-if="isRecommended(domain.id)" class="recommended-badge">
          {{ t('analysis.recommended') }}
        </div>
      </div>
    </div>

    <div class="scenario-enhancer">
      <h4 class="enhancer-title">{{ t('analysis.scenarioEnhancement') }}</h4>
      <textarea 
        v-model="scenarioDescription" 
        :placeholder="t('analysis.scenarioPlaceholder')"
        class="scenario-input"
        rows="3"
      ></textarea>
      <div v-if="dynamicAgentSuggestions.length > 0" class="dynamic-suggestions">
        <p class="suggestions-title">{{ t('analysis.suggestedAgents') }}</p>
        <div class="suggestion-list">
          <div v-for="agent in dynamicAgentSuggestions" :key="agent.templateId" class="suggestion-item">
            <i :class="getAgentIcon(agent.templateType)"></i>
            <span class="agent-name">{{ agent.name }}</span>
            <span class="agent-reason">{{ agent.reason }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="selection-summary">
      <div class="summary-stats">
        <div class="stat-item">
          <span class="stat-label">{{ t('analysis.selectedDomains') }}</span>
          <span class="stat-value">{{ selectedDomains.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t('analysis.estimatedAgents') }}</span>
          <span class="stat-value">{{ estimatedAgentCount }}</span>
        </div>
        <div v-if="dynamicAgentCount > 0" class="stat-item">
          <span class="stat-label">{{ t('analysis.dynamicAgents') }}</span>
          <span class="stat-value">+{{ dynamicAgentCount }}</span>
        </div>
      </div>
      <button 
        @click="confirmSelection" 
        :disabled="selectedDomains.length === 0"
        class="confirm-button"
      >
        {{ t('analysis.startAnalysis') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAnalysisStore } from '@/stores/analysis'
import type { AnalysisDomain, MarketType } from '@/types/analysis'

// 显式定义组件名称以提高 Vetur 兼容性
defineOptions({
  name: 'DynamicDomainSelector'
})

const { t } = useI18n()
const analysisStore = useAnalysisStore()

const emit = defineEmits<{
  'domains-selected': [domains: string[], marketType: string, scenario?: string]
}>()

// 响应式数据
const selectedMarketType = ref<string>('crypto')
const selectedDomains = ref<string[]>([])
const scenarioDescription = ref('')
const dynamicAgentSuggestions = ref<any[]>([])

// 可用领域列表（现在只支持crypto市场）
const availableDomains = computed(() => {
  const allDomains = [
    { id: 'technical', name: t('analysis.domains.technical'), description: t('analysis.domains.technicalDesc') },
    { id: 'sentiment', name: t('analysis.domains.sentiment'), description: t('analysis.domains.sentimentDesc') },
    { id: 'risk', name: t('analysis.domains.risk'), description: t('analysis.domains.riskDesc') },
    { id: 'market', name: t('analysis.domains.market'), description: t('analysis.domains.marketDesc') },
    { id: 'onchain', name: t('analysis.domains.onchain'), description: t('analysis.domains.onchainDesc') },
    { id: 'defi', name: t('analysis.domains.defi'), description: t('analysis.domains.defiDesc') },
    { id: 'event', name: t('analysis.domains.event'), description: t('analysis.domains.eventDesc') },
    { id: 'probability', name: t('analysis.domains.probability'), description: t('analysis.domains.probabilityDesc') },
    { id: 'odds', name: t('analysis.domains.odds'), description: t('analysis.domains.oddsDesc') },
  ]

  // 只返回crypto相关的领域
  return allDomains
})

// 推荐的领域（crypto市场）
const recommendedDomains = computed(() => {
  return ['technical', 'onchain', 'defi', 'sentiment']
})

// 估算agent数量
const estimatedAgentCount = computed(() => {
  // 基础估算逻辑
  const baseCount = selectedDomains.value.length * 1.5
  return Math.ceil(baseCount)
})

// 动态agent数量
const dynamicAgentCount = computed(() => dynamicAgentSuggestions.value.length)

// 方法
const isSelected = (domainId: string) => selectedDomains.value.includes(domainId)
const isRecommended = (domainId: string) => recommendedDomains.value.includes(domainId)

const toggleDomain = (domainId: string) => {
  const index = selectedDomains.value.indexOf(domainId)
  if (index > -1) {
    selectedDomains.value.splice(index, 1)
  } else {
    selectedDomains.value.push(domainId)
  }
}

const onMarketTypeChange = () => {
  // 清除不适用的选择
  selectedDomains.value = selectedDomains.value.filter(d => 
    availableDomains.value.some(ad => ad.id === d)
  )
}

const getDomainIcon = (domainId: string) => {
  const iconMap: Record<string, string> = {
    technical: 'i-carbon-chart-line',
    fundamental: 'i-carbon-document',
    sentiment: 'i-carbon-face-satisfied',
    risk: 'i-carbon-warning',
    market: 'i-carbon-globe',
    valuation: 'i-carbon-currency',
    sector: 'i-carbon-industry',
    onchain: 'i-carbon-blockchain',
    defi: 'i-carbon-finance',
    event: 'i-carbon-calendar',
    probability: 'i-carbon-analytics',
    odds: 'i-carbon-percentage'
  }
  return iconMap[domainId] || 'i-carbon-help'
}

const getAgentIcon = (templateType: string) => {
  const iconMap: Record<string, string> = {
    specialist: 'i-carbon-user-certification',
    analyst: 'i-carbon-analytics',
    researcher: 'i-carbon-microscope',
    strategist: 'i-carbon-strategy-play',
    validator: 'i-carbon-checkmark-filled'
  }
  return iconMap[templateType] || 'i-carbon-user'
}

// 监听场景描述变化，获取动态agent建议
watch(scenarioDescription, async (newValue) => {
  if (newValue.length > 10) {
    // 这里应该调用API获取建议
    // 暂时使用模拟数据
    dynamicAgentSuggestions.value = [
      { templateId: 'industry_expert', name: '行业专家', templateType: 'specialist', reason: '深入分析行业趋势' },
      { templateId: 'esg_specialist', name: 'ESG分析专家', templateType: 'specialist', reason: '评估可持续发展' }
    ]
  } else {
    dynamicAgentSuggestions.value = []
  }
})

const confirmSelection = () => {
  emit('domains-selected', selectedDomains.value, selectedMarketType.value, scenarioDescription.value)
}
</script>

<style scoped>
.dynamic-domain-selector {
  @apply p-6 bg-[var(--color-surface)] rounded-lg;
}

.selector-header {
  @apply flex justify-between items-center mb-6;
}

.selector-title {
  @apply text-xl font-semibold text-[var(--color-text)];
}

.market-type-selector {
  @apply flex items-center gap-3;
}

.market-label {
  @apply text-sm text-[var(--color-text-secondary)];
}

.market-select {
  @apply px-3 py-1.5 bg-[var(--color-background)] border border-[var(--color-border)] 
         rounded-md text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)];
}

.domains-grid {
  @apply grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6;
}

.domain-card {
  @apply p-4 bg-[var(--color-background)] border-2 border-[var(--color-border)] 
         rounded-lg cursor-pointer transition-all hover:border-[var(--color-primary)]
         hover:shadow-md relative;
}

.domain-card.selected {
  @apply border-[var(--color-primary)] bg-[var(--color-primary-bg)];
}

.domain-card.recommended {
  border-color: rgba(var(--color-success-rgb), 0.3);
}

.domain-icon {
  @apply text-2xl text-[var(--color-primary)] mb-2;
}

.domain-info {
  @apply space-y-1;
}

.domain-name {
  @apply font-medium text-[var(--color-text)];
}

.domain-description {
  @apply text-sm text-[var(--color-text-secondary)];
}

.recommended-badge {
  @apply absolute top-2 right-2 px-2 py-0.5 text-xs rounded-full;
  background-color: rgba(var(--color-success-rgb), 0.1);
  color: var(--color-success);
}

.scenario-enhancer {
  @apply mb-6 p-4 bg-[var(--color-background)] rounded-lg;
}

.enhancer-title {
  @apply font-medium text-[var(--color-text)] mb-3;
}

.scenario-input {
  @apply w-full px-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)]
         rounded-md text-[var(--color-text)] resize-none focus:outline-none 
         focus:border-[var(--color-primary)];
}

.dynamic-suggestions {
  @apply mt-4;
}

.suggestions-title {
  @apply text-sm font-medium text-[var(--color-text-secondary)] mb-2;
}

.suggestion-list {
  @apply space-y-2;
}

.suggestion-item {
  @apply flex items-center gap-3 p-2 bg-[var(--color-surface)] rounded-md;
}

.agent-name {
  @apply font-medium text-[var(--color-text)];
}

.agent-reason {
  @apply text-sm text-[var(--color-text-secondary)] ml-auto;
}

.selection-summary {
  @apply flex justify-between items-center p-4 bg-[var(--color-background)] rounded-lg;
}

.summary-stats {
  @apply flex gap-6;
}

.stat-item {
  @apply flex flex-col;
}

.stat-label {
  @apply text-sm text-[var(--color-text-secondary)];
}

.stat-value {
  @apply text-xl font-semibold text-[var(--color-text)];
}

.confirm-button {
  @apply px-6 py-2 bg-[var(--color-primary)] text-white rounded-md
         hover:bg-[var(--color-primary-hover)] disabled:opacity-50 
         disabled:cursor-not-allowed transition-colors;
}
</style>