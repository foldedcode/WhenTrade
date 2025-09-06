<template>
  <div v-if="visible" class="terminal-modal-overlay" @click="handleBackdropClick">
    <div class="terminal-report-container card--od--refined" @click.stop>
      <!-- 终端风格报告头部 -->
      <div class="section__header--od section__header--od--dark">
        <div class="flex items-center space-x-3">
          <div class="terminal-report-icon">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <div class="section__title--od">{{ t('analysis.detail.title', { symbol: analysis?.config?.symbol }) }}</div>
            <div class="section__subtitle--od">{{ t('analysis.detail.subtitle', { type: getMarketType(analysis?.config?.marketType), date: formatDate(analysis?.timestamp), id: analysis?.id?.slice(-8) }) }}</div>
          </div>
        </div>
        
        <button @click="close" class="btn--od btn--od--ghost btn--od--sm">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 主要内容区域 -->
      <div class="flex-1 flex flex-col min-h-0">
        <div class="flex-1 flex flex-col min-h-0">
          
          <!-- 终端内容区域 -->
          <div class="flex-1 overflow-y-auto section__content--od">
            <!-- 极简分析报告 -->
            <SimpleReport ref="reportRef" :analysis="adaptedAnalysis" />
          </div>
        </div>
      </div>
        
      <!-- 终端风格操作栏 -->
      <div class="section__header--od section__header--od--dark border-t">
        <div></div>
        <div class="section__actions--od">
          <button @click="exportReport" class="btn--od btn--od--secondary btn--od--sm">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {{ t('analysis.detail.actions.export') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SimpleReport from '@/components/report/SimpleReport.vue'

interface AnalysisThought {
  agent?: string
  thought: string
  timestamp: string
  phase?: string
  phaseName?: string
  isTool?: boolean
  tool?: string
}

interface AnalysisDetail {
  id: string
  timestamp: number
  config: {
    symbol: string
    marketType: string
    depth: number
    analysts: string[]
    llmProvider: string
    llmModel: string
  }
  cost: number
  duration: number
  result: any
  agentThoughts: AnalysisThought[]
}

interface Props {
  visible: boolean
  analysis: AnalysisDetail | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  export: [analysis: AnalysisDetail]
}>()

const { t } = useI18n()

// 获取报告组件引用
const reportRef = ref()

// 类型转换适配器：将 AnalysisDetail 转换为 SimpleReport 期望的 Analysis 类型
const adaptedAnalysis = computed(() => {
  if (!props.analysis) return null
  
  return {
    id: props.analysis.id,
    timestamp: props.analysis.timestamp,
    duration: props.analysis.duration,
    config: {
      symbol: props.analysis.config.symbol,
      marketType: props.analysis.config.marketType,
      depth: props.analysis.config.depth
    },
    agentThoughts: props.analysis.agentThoughts || []
  }
})


// 处理点击背景关闭
const handleBackdropClick = (event: MouseEvent) => {
  // 阻止事件冒泡，避免在点击modal内容时关闭
  if (event.target === event.currentTarget) {
    close()
  }
}

// 方法
const close = () => {
  emit('close')
}

const formatDuration = (duration: number | undefined) => {
  if (!duration) return t('report.duration.unknown')
  const seconds = Math.floor(duration / 1000)
  if (seconds < 60) {
    return t('report.duration.seconds', { seconds })
  } else {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return t('report.duration.minutesSeconds', { minutes, seconds: remainingSeconds })
  }
}

const exportReport = () => {
  if (!props.analysis || !reportRef.value) {
    return
  }
  
  // 调用报告组件的打印功能导出PDF
  reportRef.value.print()
}


const formatDate = (timestamp: number | undefined) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString()
}

const getMarketType = (type: string | undefined) => {
  if (!type) return t('common.marketTypes.unknown')
  const validTypes = ['crypto']
  const typeKey = validTypes.includes(type) ? type : 'unknown'
  return t(`common.marketTypes.${typeKey}`)
}
</script>

<style scoped>
/* 样式保持不变，继承现有的终端风格 */
.terminal-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.terminal-report-container {
  width: 90vw;
  height: 90vh;
  max-width: 1200px;
  display: flex;
  flex-direction: column;
}

.terminal-report-icon {
  color: #00ff00;
}
</style>