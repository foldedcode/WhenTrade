<template>
  <div class="report-viewer">
    <div class="panel-header">
      <span class="header-title">分析报告</span>
      <div class="header-actions">
        <button 
          v-if="report" 
          @click="copyReport" 
          class="action-btn"
          title="复制报告"
        >
          📋
        </button>
        <button 
          v-if="report" 
          @click="downloadReport" 
          class="action-btn"
          title="下载报告"
        >
          💾
        </button>
      </div>
    </div>
    
    <div class="report-content">
      <!-- 加载中状态 -->
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner">
          <div class="spinner-ring"></div>
        </div>
        <div class="loading-text">正在生成分析报告...</div>
        <div class="loading-stages">
          <div class="stage-item">
            <span class="stage-dot active"></span>
            <span>收集数据</span>
          </div>
          <div class="stage-item">
            <span class="stage-dot"></span>
            <span>分析处理</span>
          </div>
          <div class="stage-item">
            <span class="stage-dot"></span>
            <span>生成报告</span>
          </div>
        </div>
      </div>
      
      <!-- 报告内容 -->
      <div v-else-if="report" class="report-display">
        <div class="report-markdown" v-html="renderedReport"></div>
      </div>
      
      <!-- 空状态 -->
      <div v-else class="empty-state">
        <div class="empty-icon">📊</div>
        <div class="empty-text">暂无分析报告</div>
        <div class="empty-hint">完成分析后将在此处显示详细报告</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

interface Props {
  report?: string
  isLoading?: boolean
}

const props = defineProps<Props>()

// 配置marked
marked.setOptions({
  breaks: true,
  gfm: true
})

// 计算属性 - 渲染Markdown
const renderedReport = computed(() => {
  if (!props.report) return ''
  
  try {
    // 渲染Markdown并添加自定义样式
    let html = marked.parse(props.report)
    
    // 为代码块添加语法高亮类
    html = html.replace(/<pre>/g, '<pre class="code-block">')
    
    // 为表格添加样式类
    html = html.replace(/<table>/g, '<table class="report-table">')
    
    return html
  } catch (error) {
    console.error('Failed to render markdown:', error)
    return `<pre>${props.report}</pre>`
  }
})

// 方法
const copyReport = () => {
  if (props.report) {
    navigator.clipboard.writeText(props.report).then(() => {
      console.log('报告已复制到剪贴板')
    }).catch(err => {
      console.error('复制失败:', err)
    })
  }
}

const downloadReport = () => {
  if (props.report) {
    const blob = new Blob([props.report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analysis-report-${Date.now()}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
}
</script>

<style lang="scss" scoped>
.report-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: #00ff41;
  font-family: 'Proto Mono', monospace;
  font-size: 12px;
}

.panel-header {
  padding: 0.75rem 1rem;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .header-title {
    color: var(--od-primary-light);
    font-weight: bold;
    text-transform: uppercase;
    font-size: 13px;
  }
  
  .header-actions {
    display: flex;
    gap: 0.5rem;
    
    .action-btn {
      padding: 0.25rem 0.5rem;
      background: #0f0f0f;
      border: 1px solid #333;
      border-radius: 3px;
      color: #888;
      font-size: 14px;
      cursor: pointer;
      transition: all 0.2s;
      
      &:hover {
        background: #1a1a1a;
        border-color: #00ff41;
        color: #00ff41;
      }
    }
  }
}

.report-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: #0a0a0a;
  
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
    
    .loading-spinner {
      margin-bottom: 1.5rem;
      
      .spinner-ring {
        width: 48px;
        height: 48px;
        border: 3px solid #1a1a1a;
        border-top: 3px solid var(--od-primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }
    }
    
    .loading-text {
      color: var(--od-primary-light);
      font-size: 14px;
      margin-bottom: 1.5rem;
    }
    
    .loading-stages {
      display: flex;
      gap: 1.5rem;
      
      .stage-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #666;
        font-size: 11px;
        
        .stage-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #333;
          transition: all 0.3s;
          
          &.active {
            background: var(--od-primary);
            box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
          }
        }
      }
    }
  }
  
  .report-display {
    padding: 2rem;
    
    .report-markdown {
      color: #e0e0e0;
      line-height: 1.6;
      
      // Markdown样式
      :deep(h1) {
        color: var(--od-primary-light);
        font-size: 20px;
        margin: 1.5rem 0 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #333;
      }
      
      :deep(h2) {
        color: #00ff41;
        font-size: 16px;
        margin: 1.25rem 0 0.75rem;
      }
      
      :deep(h3) {
        color: #3b82f6;
        font-size: 14px;
        margin: 1rem 0 0.5rem;
      }
      
      :deep(p) {
        margin: 0.75rem 0;
      }
      
      :deep(ul), :deep(ol) {
        margin: 0.75rem 0;
        padding-left: 1.5rem;
        
        li {
          margin: 0.25rem 0;
        }
      }
      
      :deep(blockquote) {
        margin: 1rem 0;
        padding: 0.75rem 1rem;
        background: rgba(74, 222, 128, 0.05);
        border-left: 3px solid var(--od-primary);
        color: var(--od-primary-light);
      }
      
      :deep(code) {
        padding: 0.125rem 0.375rem;
        background: #1a1a1a;
        border-radius: 3px;
        color: #00ff41;
        font-family: 'Proto Mono', monospace;
        font-size: 11px;
      }
      
      :deep(pre) {
        &.code-block {
          margin: 1rem 0;
          padding: 1rem;
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 4px;
          overflow-x: auto;
          
          code {
            padding: 0;
            background: none;
            color: #e0e0e0;
          }
        }
      }
      
      :deep(table) {
        &.report-table {
          width: 100%;
          margin: 1rem 0;
          border-collapse: collapse;
          
          th, td {
            padding: 0.5rem;
            border: 1px solid #333;
            text-align: left;
          }
          
          th {
            background: #1a1a1a;
            color: var(--od-primary-light);
            font-weight: bold;
          }
          
          tr:nth-child(even) {
            background: rgba(255, 255, 255, 0.02);
          }
        }
      }
      
      :deep(hr) {
        margin: 1.5rem 0;
        border: none;
        border-top: 1px solid #333;
      }
      
      :deep(strong) {
        color: #00ff41;
        font-weight: bold;
      }
      
      :deep(em) {
        color: var(--od-primary-light);
        font-style: italic;
      }
      
      :deep(a) {
        color: #3b82f6;
        text-decoration: none;
        
        &:hover {
          text-decoration: underline;
        }
      }
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

// 动画
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

// 滚动条样式
.report-content::-webkit-scrollbar {
  width: 6px;
}

.report-content::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.report-content::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
  
  &:hover {
    background: #444;
  }
}
</style>