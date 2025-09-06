<template>
  <div class="message-stream">
    <!-- 消息过滤器移到顶部 -->
    <div class="message-filters">
      <button 
        v-for="filter in filters" 
        :key="filter.type"
        @click="toggleFilter(filter.type)"
        :class="['filter-btn', { active: filterStates[filter.type] }]"
        :style="{ '--filter-color': filter.color }"
      >
        {{ filter.label }}
      </button>
    </div>
    
    <div class="message-content" ref="messageContainer" @scroll="handleScroll">
      
      <!-- 消息列表 -->
      <div 
        v-for="(msg, idx) in filteredMessages" 
        :key="idx"
        class="message-line"
        :class="[`type-${msg.type}`]"
      >
        <span class="msg-time">{{ msg.time }}</span>
        <span class="msg-type" :class="`type-badge-${msg.type}`">
          {{ getMessageTypeName(msg.type) }}
        </span>
        <span v-if="msg.agent" class="msg-agent">[{{ getLocalizedAgentName(msg.agent) }}]</span>
        <span class="msg-content" v-html="renderContent(msg.content, idx)"></span>
        <button 
          v-if="needsExpand(msg.content)"
          @click="toggleExpand(idx)"
          class="expand-btn"
        >
          {{ expandedMessages.has(idx) ? $t('analysis.stream.collapse') : $t('analysis.stream.expand') }}
        </button>
      </div>
      
      <!-- 分析完成后的报告按钮 -->
      <div v-if="!isAnalyzing && hasReport" class="report-ready">
        <div class="report-ready-content">
          <div class="success-icon">✅</div>
          <div class="success-message">{{ $t('analysis.stream.done') }}</div>
          <button @click="emit('view-report')" class="view-report-btn">
            📊 {{ $t('analysis.stream.seeReport') }}
          </button>
        </div>
      </div>
      
      <!-- 正在分析指示器 -->
      <div v-else-if="isAnalyzing" class="analyzing-indicator">
        <span class="indicator-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </span>
        <span class="indicator-text">
          <template v-if="currentAgent">{{ getLocalizedAgentName(currentAgent) }} - </template>
          {{ $t('analysis.stream.thinking') }}
        </span>
        <span class="cursor-blink">_</span>
      </div>
      
      <!-- 空状态 -->
      <div v-if="!messages.length && !isAnalyzing" class="empty-state">
        <div class="empty-icon">📝</div>
        <div class="empty-text">{{ $t('analysis.stream.waiting') }}</div>
        <div class="empty-hint">{{ $t('analysis.stream.hintStart') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { useI18n } from 'vue-i18n'

// 显式定义组件名称以提高 Vetur 兼容性
defineOptions({
  name: 'MessageStream'
})

// 配置marked选项
marked.setOptions({
  breaks: true,  // 将换行符转换为<br>
  gfm: true     // 支持GitHub风格Markdown
})

interface Message {
  time: string
  type: 'system' | 'agent' | 'tool' | 'error'
  content: string
  agent?: string
}


interface Props {
  messages: Message[]
  isAnalyzing: boolean
  hasReport?: boolean
  currentAgent?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'view-report': []
}>()

// 响应式数据
const { t } = useI18n()

// Agent名称映射表 - 与父组件保持一致
const agentNameMap: Record<string, string> = {
  // 英文名称映射
  'Market Analyst': 'market',
  'Social Analyst': 'social',
  'Social Media Analyst': 'social',
  'News Analyst': 'news',
  'Fundamentals Analyst': 'fundamentals',
  'Bull Researcher': 'bull',
  'Bear Researcher': 'bear',
  'Research Manager': 'manager',
  'Trader': 'trader',
  'Risky Analyst': 'risky',
  'Neutral Analyst': 'neutral',
  'Safe Analyst': 'safe',
  'Risk Judge': 'judge',
  'Portfolio Manager': 'portfolio',
  
  // 中文名称映射
  '市场分析师': 'market',
  '社交媒体分析师': 'social',
  '新闻分析师': 'news',
  '基本面分析师': 'fundamentals',
  '链上分析师': 'onchain',
  '多头研究员': 'bull',
  '空头研究员': 'bear',
  '研究经理': 'manager',
  '交易员': 'trader',
  '激进分析师': 'risky',
  '保守分析师': 'safe',
  '中性分析师': 'neutral',
  '风险评估': 'judge',
  '组合经理': 'portfolio'
}

// 获取Agent ID
const getAgentId = (agentName: string): string => {
  if (!agentName) return ''
  const mappedId = agentNameMap[agentName]
  if (mappedId) return mappedId
  return agentName.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_')
}

// 获取本地化Agent名称
const getLocalizedAgentName = (agentName: string): string => {
  if (!agentName) return ''
  const agentId = getAgentId(agentName)
  const key = `agents.names.${agentId}`
  const translated = t(key)
  return translated !== key ? translated : agentName
}
const messageContainer = ref<HTMLElement>()

// 过滤器计算属性
const filters = computed(() => [
  { type: 'system', label: t('common.system'), active: true, color: '#00ff41' },
  { type: 'agent', label: t('common.agent'), active: true, color: '#f59e0b' },
  { type: 'tool', label: t('common.tool'), active: true, color: '#3b82f6' },
  { type: 'error', label: t('common.error.title'), active: true, color: '#dc2626' }
])

// 过滤器状态管理
const filterStates = ref<Record<string, boolean>>({
  system: true,
  agent: true,
  tool: true,
  error: true
})

// 展开状态管理
const expandedMessages = ref<Set<number>>(new Set())
const CONTENT_PREVIEW_LENGTH = 300  // 预览长度

// 用户是否在底部状态跟踪
const isUserAtBottom = ref(true) // 默认在底部


// 智能体执行状态跟踪已删除

// 过滤后的消息
const filteredMessages = computed(() => {
  const activeFilters = Object.entries(filterStates.value)
    .filter(([_, active]) => active)
    .map(([type, _]) => type)
  
  const filtered = props.messages.filter(msg => 
    activeFilters.includes(msg.type)
  )
  
  // 按时间戳排序，确保消息按正确顺序显示
  return filtered.sort((a, b) => {
    const timeA = new Date(a.time).getTime()
    const timeB = new Date(b.time).getTime()
    return timeA - timeB
  })
})


// 方法
const getMessageTypeName = (type: string) => {
  const typeNames: Record<string, string> = {
    system: 'SYS',
    agent: 'AGT',
    tool: 'TOOL',
    error: 'ERR'
  }
  return typeNames[type] || type.toUpperCase()
}

const toggleFilter = (type: string) => {
  filterStates.value[type as keyof typeof filterStates.value] = !filterStates.value[type as keyof typeof filterStates.value]
}

// 展开/收起消息
const toggleExpand = (idx: number) => {
  if (expandedMessages.value.has(idx)) {
    expandedMessages.value.delete(idx)
  } else {
    expandedMessages.value.add(idx)
  }
}

// 判断是否需要展开按钮
const needsExpand = (content: string) => {
  return content && content.length > CONTENT_PREVIEW_LENGTH
}

// 渲染Markdown内容
const renderContent = (content: string, idx: number) => {
  if (!content) return ''
  
  // 检查是否为翻译键并进行翻译
  let displayContent = content
  if (content.includes('.') && (content.startsWith('analysis.') || content.startsWith('common.'))) {
    try {
      displayContent = t(content)
    } catch (e) {
      // 如果翻译失败，使用原内容
      displayContent = content
    }
  }
  
  // 处理展开/收起逻辑
  if (needsExpand(displayContent) && !expandedMessages.value.has(idx)) {
    displayContent = displayContent.substring(0, CONTENT_PREVIEW_LENGTH) + '...'
  }
  
  // 内容预处理
  const preprocessContent = (text: string): string => {
    // 1. 处理对话式内容，在说话者标识前添加额外换行
    const speakers = [
      '看涨分析师', '看跌分析师', '研究经理', '交易员', '风险分析师', 
      '组合经理', '市场分析师', '社交媒体分析师', '新闻分析师', 
      '基本面分析师', '链上分析师', 'DeFi分析师', '激进辩手', 
      '保守辩手', '中立辩手', '风险裁判'
    ]
    const speakerPattern = new RegExp(`(^|\\n)(${speakers.join('|')})：`, 'gm')
    text = text.replace(speakerPattern, '\n\n$2：')
    
    // 2. 处理列表项，确保列表格式正确
    text = text.replace(/^(\s*)[-*+]\s+/gm, '- ')  // 统一列表标记为 -
    text = text.replace(/^(\s*)\d+\.\s+/gm, (match) => {
      // 保留数字列表的格式
      return match.replace(/^\s+/, '')
    })
    
    // 3. 移除不一致的缩进（除了代码块和列表）
    const lines = text.split('\n')
    const processedLines = []
    let inCodeBlock = false
    
    for (const line of lines) {
      // 检测代码块边界
      if (line.replace(/^\s+/, '').startsWith('```')) {
        inCodeBlock = !inCodeBlock
        processedLines.push(line)
        continue
      }
      
      // 代码块内的内容保持原样
      if (inCodeBlock) {
        processedLines.push(line)
        continue
      }
      
      // 列表项保持适当缩进
      if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
        processedLines.push(line.replace(/^\s+/, ''))
        continue
      }
      
      // 标题行不缩进
      if (line.replace(/^\s+/, '').startsWith('#')) {
        processedLines.push(line.replace(/^\s+/, ''))
        continue
      }
      
      // 其他内容移除前导空格
      processedLines.push(line.replace(/^\s+/, ''))
    }
    
    text = processedLines.join('\n')
    
    // 4. 确保段落之间有适当的分隔
    // 在标题后添加换行
    text = text.replace(/(^#{1,6}\s+.+$)/gm, '$1\n')
    
    // 5. 清理多余的空行（超过2个连续空行变为2个）
    text = text.replace(/\n{3,}/g, '\n\n')
    
    // 6. 确保开头没有多余的空行
    text = text.replace(/^\s+/, '')
    
    return text
  }
  
  // 应用预处理
  displayContent = preprocessContent(displayContent)
  
  // 渲染Markdown
  try {
    // 使用marked渲染Markdown
    const html = marked.parse(displayContent)
    return html
  } catch (e) {
    // 如果解析失败，至少保留换行
    console.warn('Markdown解析失败:', e)
    return displayContent.replace(/\n/g, '<br>')
  }
}

// 滚动到底部（无条件滚动）
const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight
    }
  })
}

// 用户滚动事件处理
const handleScroll = () => {
  if (!messageContainer.value) return
  const container = messageContainer.value
  // 判断用户是否在底部附近（容差50px）
  isUserAtBottom.value = container.scrollHeight - container.scrollTop - container.clientHeight < 50
}

// 智能体消息解析功能已删除


// 监听消息变化（智能体解析已删除）

watch(() => filteredMessages.value.length, () => {
  // 如果用户之前在底部，则自动滚动到新消息
  if (isUserAtBottom.value) {
    scrollToBottom()
  }
})

// 组件挂载时滚动到底部
onMounted(() => {
  scrollToBottom()
})
</script>

<style lang="scss" scoped>
.message-stream {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: var(--od-text-primary);
  font-family: 'Proto Mono', monospace;
  font-size: 12px;
  background: var(--od-background);
}

.message-content {
  flex: 1;
  padding: 0.75rem;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--od-background);
  
  .message-line {
    display: flex;
    align-items: flex-start;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.25rem;
    background: var(--od-background-alt);
    border-left: 2px solid transparent;
    transition: all 0.2s;
    font-size: 11px;
    line-height: 1.4;
    border-radius: var(--border-radius-sm);
    
    &.highlight {
      background: var(--od-background);
      border-left-color: var(--od-primary);
    }
    
    &.type-system {
      .msg-content { color: var(--od-primary-light); }
    }
    
    &.type-agent {
      .msg-content { color: var(--od-accent); }
    }
    
    &.type-tool {
      .msg-content { color: var(--od-info); }
    }
    
    
    &.type-error {
      background: var(--od-background);
      border-left-color: var(--od-error);
      .msg-content { color: var(--od-error); }
    }
    
    .msg-time {
      color: var(--od-text-muted);
      margin-right: 0.5rem;
      flex-shrink: 0;
    }
    
    .msg-type {
      padding: 0.125rem 0.375rem;
      border-radius: 3px;
      font-size: 10px;
      font-weight: bold;
      margin-right: 0.5rem;
      flex-shrink: 0;
      
      &.type-badge-system {
        background: linear-gradient(135deg, var(--od-primary), var(--od-primary-light));
        color: var(--od-background);
      }
      
      &.type-badge-agent {
        background: var(--od-accent);
        color: var(--od-background);
      }
      
      &.type-badge-tool {
        background: var(--od-info);
        color: var(--od-background);
      }
      
      
      &.type-badge-error {
        background: var(--od-error);
        color: white;
      }
    }
    
    .msg-agent {
      color: var(--od-text-secondary);
      margin-right: 0.5rem;
      flex-shrink: 0;
    }
    
    .msg-content {
      flex: 1;
      word-break: break-word;
      line-height: 1.6;
      
      // Markdown样式
      :deep(p) { 
        margin: 0.4em 0;
        &:first-child { margin-top: 0; }
        &:last-child { margin-bottom: 0; }
      }
      
      :deep(strong) { 
        color: var(--od-accent);
        font-weight: 600;
      }
      
      :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) { 
        margin: 0.8em 0 0.4em;
        color: var(--od-primary);
        font-weight: 600;
        &:first-child { margin-top: 0; }
      }
      
      :deep(h1) { font-size: 18px; }
      :deep(h2) { font-size: 16px; }
      :deep(h3) { font-size: 14px; }
      :deep(h4) { font-size: 13px; }
      
      :deep(ul), :deep(ol) { 
        margin: 0.5em 0;
        padding-left: 1.5em;
      }
      
      :deep(li) {
        margin: 0.2em 0;
      }
      
      :deep(code) {
        background: var(--od-background);
        color: var(--od-primary-light);
        padding: 0.1em 0.3em;
        border-radius: 3px;
        font-family: 'Proto Mono', monospace;
        font-size: 0.9em;
      }
      
      :deep(pre) {
        background: var(--od-background);
        padding: 0.8em;
        border-radius: 4px;
        overflow-x: auto;
        margin: 0.5em 0;
        
        code {
          background: none;
          padding: 0;
        }
      }
      
      :deep(blockquote) {
        border-left: 3px solid var(--od-primary);
        padding-left: 1em;
        margin: 0.5em 0;
        color: var(--od-text-secondary);
      }
      
      :deep(hr) {
        border: none;
        border-top: 1px solid var(--od-border);
        margin: 1em 0;
      }
      
      :deep(a) {
        color: var(--od-info);
        text-decoration: none;
        &:hover {
          text-decoration: underline;
        }
      }
    }
    
    .expand-btn {
      margin-left: 0.5rem;
      padding: 0.125rem 0.5rem;
      background: transparent;
      border: 1px solid var(--od-border);
      color: var(--od-primary);
      font-size: 10px;
      cursor: pointer;
      border-radius: 3px;
      transition: all 0.2s;
      
      &:hover {
        background: var(--od-primary);
        color: var(--od-background);
      }
    }
  }
  
  .report-ready {
    margin-top: 1rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, rgba(0, 255, 65, 0.1), rgba(245, 158, 11, 0.05));
    border: 1px solid #00ff41;
    border-radius: 8px;
    animation: glow 2s ease-in-out infinite;
    
    .report-ready-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      
      .success-icon {
        font-size: 48px;
        animation: bounce 1s;
      }
      
      .success-message {
        color: #00ff41;
        font-size: 16px;
        font-weight: bold;
      }
      
      .view-report-btn {
        padding: 0.75rem 2rem;
        background: linear-gradient(135deg, #00ff41, #00cc33);
        border: none;
        border-radius: 6px;
        color: #000;
        font-size: 14px;
        font-weight: bold;
        font-family: inherit;
        cursor: pointer;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(0, 255, 65, 0.3);
        
        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(0, 255, 65, 0.5);
        }
        
        &:active {
          transform: translateY(0);
        }
      }
    }
  }
  
  .analyzing-indicator {
    display: flex;
    align-items: center;
    padding: 0.75rem;
    margin-top: 0.5rem;
    background: rgba(245, 158, 11, 0.1);
    border-radius: 4px;
    
    .indicator-dots {
      display: flex;
      gap: 0.25rem;
      margin-right: 0.75rem;
      
      .dot {
        width: 6px;
        height: 6px;
        background: #f59e0b;
        border-radius: 50%;
        animation: bounce 1.4s infinite ease-in-out both;
        
        &:nth-child(1) { animation-delay: -0.32s; }
        &:nth-child(2) { animation-delay: -0.16s; }
      }
    }
    
    .indicator-text {
      color: #f59e0b;
      font-style: italic;
    }
    
    .cursor-blink {
      color: #f59e0b;
      animation: blink 1s infinite;
      margin-left: 0.125rem;
    }
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
    text-align: center;
    
    .empty-icon {
      font-size: 48px;
      margin-bottom: 1rem;
      opacity: 0.5;
    }
    
    .empty-text {
      color: #888;
      margin-bottom: 0.5rem;
    }
    
    .empty-hint {
      color: #666;
      font-size: 11px;
    }
  }
}

.message-filters {
  padding: 0.5rem;
  background: var(--od-background-alt);
  border-bottom: 1px solid var(--od-border);
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  
  .filter-btn {
    padding: 0.25rem 0.75rem;
    background: var(--od-background);
    border: 1px solid var(--od-border);
    border-radius: var(--border-radius-sm);
    color: var(--od-text-secondary);
    font-size: 11px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.2s;
    
    &.active {
      background: linear-gradient(135deg, 
        rgba(78, 201, 176, 0.05) 0%, 
        rgba(78, 201, 176, 0.02) 100%);
      border-color: var(--od-primary);
      color: var(--od-primary-light);
      box-shadow: 0 0 0 1px rgba(78, 201, 176, 0.2) inset, 
                  0 0 8px rgba(78, 201, 176, 0.15);
      font-weight: 500;
    }
    
    &:hover:not(.active) {
      border-color: rgba(78, 201, 176, 0.5);
      color: var(--od-primary);
      background: rgba(78, 201, 176, 0.03);
      transform: translateY(-1px);
      box-shadow: 0 2px 4px rgba(78, 201, 176, 0.1);
    }
  }
}

// 动画
@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes glow {
  0%, 100% {
    box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
  }
  50% {
    box-shadow: 0 0 30px rgba(0, 255, 65, 0.5);
  }
}

// 智能体时序指示器样式已删除

// 滚动条样式
.message-content::-webkit-scrollbar {
  width: 6px;
}

.message-content::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.message-content::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
  
  &:hover {
    background: #444;
  }
}

// pulse动画已删除（用于智能体时序指示器）
</style>