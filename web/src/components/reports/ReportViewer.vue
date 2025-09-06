<template>
  <div class="report-wrapper">
    <article class="report-prose" v-html="html"></article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import html2pdf from 'html2pdf.js'

interface Props {
  markdown: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '分析报告'
})

const html = computed(() => {
  return marked.parse(props.markdown || '', { 
    gfm: true, 
    breaks: true 
  })
})

const print = () => {
  exportPDF()
}

const exportPDF = () => {
  const originalElement = document.querySelector('.report-prose') as HTMLElement
  if (!originalElement) {
    console.error('无法找到报告内容元素')
    return
  }

  const filename = `${props.title || '分析报告'}_${new Date().toISOString().split('T')[0]}.pdf`
  
  // 克隆元素以避免影响原始界面
  const clonedElement = originalElement.cloneNode(true) as HTMLElement
  
  // 创建临时容器（不可见）
  const tempContainer = document.createElement('div')
  tempContainer.style.position = 'absolute'
  tempContainer.style.left = '-9999px'
  tempContainer.style.top = '0'
  tempContainer.style.width = '210mm'  // A4宽度
  tempContainer.style.background = 'white'
  tempContainer.style.color = 'black'
  tempContainer.style.fontSize = '14px'
  tempContainer.style.fontFamily = 'Arial, sans-serif'
  
  // 添加克隆的元素到临时容器
  clonedElement.classList.add('pdf-export-mode')
  tempContainer.appendChild(clonedElement)
  document.body.appendChild(tempContainer)
  
  const opt = {
    margin: 10,
    filename: filename,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { 
      scale: 2, 
      useCORS: true,
      letterRendering: true,
      allowTaint: false,
      backgroundColor: '#ffffff',
      logging: false,
      windowWidth: 794,  // A4 宽度像素
      windowHeight: 1123  // A4 高度像素
    },
    jsPDF: { 
      unit: 'mm', 
      format: 'a4', 
      orientation: 'portrait' 
    },
    pagebreak: { mode: 'avoid-all' }
  }

  html2pdf()
    .set(opt)
    .from(clonedElement)
    .save()
    .then(() => {
      // 清理临时容器
      document.body.removeChild(tempContainer)
    })
    .catch((error: any) => {
      // 确保出错时也清理
      if (document.body.contains(tempContainer)) {
        document.body.removeChild(tempContainer)
      }
      console.error('PDF生成失败:', error)
    })
}

// 暴露给父组件调用
defineExpose({ print, exportPDF })
</script>

<style>
.report-wrapper { 
  background: transparent; 
  color: var(--od-text-primary, #e6e6e6); 
  padding: 16px; 
  min-height: 100vh;
}


.report-prose { 
  line-height: 1.8; 
  font-size: 14px; 
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'SF Mono', Monaco, Inconsolata, 'Roboto Mono', 'Source Code Pro', 'Courier New', monospace;
}

.report-prose h1 { 
  font-size: 20px; 
  margin: 20px 0 12px; 
  color: #00ff00;
  border-bottom: 2px solid #00ff00;
  padding-bottom: 4px;
}

.report-prose h2 { 
  font-size: 18px; 
  margin: 16px 0 8px; 
  border-left: 3px solid #10b981; 
  padding-left: 12px;
  color: #10b981;
}

.report-prose h3 { 
  font-size: 16px; 
  margin: 14px 0 6px; 
  color: #60a5fa;
}

.report-prose h4 { 
  font-size: 15px; 
  margin: 12px 0 4px; 
  color: #fbbf24;
}

.report-prose p { 
  margin: 10px 0; 
  text-align: justify;
}

.report-prose ul { 
  margin: 10px 0 10px 24px; 
  list-style: disc; 
}

.report-prose ol { 
  margin: 10px 0 10px 24px; 
  list-style: decimal; 
}

.report-prose li {
  margin: 4px 0;
}

.report-prose strong {
  color: #fbbf24;
  font-weight: 600;
}

.report-prose em {
  color: #a78bfa;
  font-style: italic;
}

.report-prose code {
  background: #1f2937;
  color: #f59e0b;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 13px;
}

.report-prose pre {
  background: var(--od-background-alt, #0f172a);
  border: 1px solid var(--od-border, #334155);
  border-radius: 6px;
  padding: 12px;
  margin: 12px 0;
  overflow-x: auto;
}

.report-prose pre code {
  background: transparent;
  color: #e2e8f0;
  padding: 0;
}

.report-prose table { 
  width: 100%; 
  border-collapse: collapse; 
  margin: 12px 0; 
  font-size: 13px; 
  background: var(--od-background-light, #1f2937);
}

.report-prose th, .report-prose td { 
  border: 1px solid var(--od-border, #374151); 
  padding: 8px 12px; 
  text-align: left;
}

.report-prose th {
  background: var(--od-background-lighter, #374151);
  font-weight: 600;
  color: var(--od-text-primary, #f3f4f6);
}

.report-prose tr:nth-child(even) {
  background: var(--od-background-alt, #111827);
}

.report-prose blockquote { 
  border-left: 4px solid var(--od-border, #4b5563); 
  margin: 12px 0; 
  padding: 8px 16px; 
  color: var(--od-text-muted, #cbd5e1); 
  background: var(--od-background-alt, #0f172a);
  border-radius: 0 4px 4px 0;
  font-style: italic;
}

.report-prose hr { 
  border: 0; 
  border-top: 2px solid var(--od-border, #374151); 
  margin: 20px 0; 
}

/* PDF导出模式样式 - 强制使用打印友好的颜色 */
.pdf-export-mode {
  background: white !important;
  color: black !important;
}

.pdf-export-mode h1 { 
  color: black !important;
  border-bottom-color: black !important;
  font-size: 18px !important;
}

.pdf-export-mode h2 { 
  color: #059669 !important;
  border-left-color: #059669 !important;
  font-size: 16px !important;
}

.pdf-export-mode h3 { 
  color: #2563eb !important;
  font-size: 15px !important;
}

.pdf-export-mode h4 { 
  color: #d97706 !important;
  font-size: 14px !important;
}

.pdf-export-mode p {
  color: black !important;
}

.pdf-export-mode strong {
  color: #b45309 !important;
  font-weight: 600 !important;
}

.pdf-export-mode em {
  color: #7c3aed !important;
  font-style: italic !important;
}

.pdf-export-mode code {
  background: #f3f4f6 !important;
  color: #dc2626 !important;
  border: 1px solid #d1d5db !important;
  padding: 2px 4px !important;
  border-radius: 3px !important;
  font-size: 12px !important;
}

.pdf-export-mode pre {
  background: #f8f9fa !important;
  border: 1px solid #dee2e6 !important;
  color: #212529 !important;
  padding: 12px !important;
  margin: 12px 0 !important;
  border-radius: 4px !important;
}

.pdf-export-mode pre code {
  background: transparent !important;
  color: #212529 !important;
  padding: 0 !important;
  border: none !important;
}

.pdf-export-mode table {
  background: white !important;
  border: 1px solid #dee2e6 !important;
  border-collapse: collapse !important;
  width: 100% !important;
  margin: 12px 0 !important;
}

.pdf-export-mode th {
  background: #f8f9fa !important;
  color: black !important;
  border: 1px solid #dee2e6 !important;
  padding: 8px 12px !important;
  font-weight: 600 !important;
  text-align: left !important;
}

.pdf-export-mode td {
  background: white !important;
  color: black !important;
  border: 1px solid #dee2e6 !important;
  padding: 8px 12px !important;
  text-align: left !important;
}

.pdf-export-mode tr:nth-child(even) {
  background: #f8f9fa !important;
}

.pdf-export-mode tr:nth-child(even) td {
  background: #f8f9fa !important;
}

.pdf-export-mode blockquote {
  background: #f8f9fa !important;
  border-left: 4px solid #6c757d !important;
  color: #495057 !important;
  margin: 12px 0 !important;
  padding: 8px 16px !important;
  border-radius: 0 4px 4px 0 !important;
  font-style: italic !important;
}

.pdf-export-mode hr {
  border: 0 !important;
  border-top: 1px solid #dee2e6 !important;
  margin: 20px 0 !important;
}

.pdf-export-mode ul {
  color: black !important;
  margin: 10px 0 10px 24px !important;
  list-style: disc !important;
}

.pdf-export-mode ol {
  color: black !important;
  margin: 10px 0 10px 24px !important;
  list-style: decimal !important;
}

.pdf-export-mode li {
  color: black !important;
  margin: 4px 0 !important;
}

/* 打印样式 */
@media print {
  body { 
    background: white !important; 
    color: black !important; 
    font-family: 'Times New Roman', serif;
  }
  
  .toolbar { 
    display: none !important; 
  }
  
  .report-wrapper { 
    padding: 0 !important; 
    background: white !important;
    color: black !important;
  }
  
  .report-prose { 
    font-size: 12pt !important; 
    line-height: 1.6 !important; 
    color: black !important;
    font-family: 'Times New Roman', serif !important;
  }
  
  .report-prose h1 { 
    color: black !important;
    border-bottom: 2px solid black !important;
    font-size: 16pt !important;
    page-break-after: avoid;
  }
  
  .report-prose h2 { 
    color: black !important;
    border-left: 3px solid black !important;
    font-size: 14pt !important;
    page-break-after: avoid;
  }
  
  .report-prose h3 { 
    color: black !important;
    font-size: 13pt !important;
    page-break-after: avoid;
  }
  
  .report-prose h4 { 
    color: black !important;
    font-size: 12pt !important;
    page-break-after: avoid;
  }
  
  .report-prose strong {
    color: black !important;
  }
  
  .report-prose em {
    color: black !important;
  }
  
  .report-prose code {
    background: #f5f5f5 !important;
    color: black !important;
    border: 1px solid #ccc !important;
  }
  
  .report-prose pre {
    background: #f8f8f8 !important;
    border: 1px solid #ccc !important;
    color: black !important;
    page-break-inside: avoid;
  }
  
  .report-prose pre code {
    color: black !important;
  }
  
  .report-prose table { 
    background: white !important;
    color: black !important;
    page-break-inside: avoid;
  }
  
  .report-prose th, .report-prose td { 
    border: 1px solid black !important;
    color: black !important;
  }
  
  .report-prose th {
    background: #f0f0f0 !important;
  }
  
  .report-prose tr:nth-child(even) {
    background: #f8f8f8 !important;
  }
  
  .report-prose blockquote { 
    border-left: 4px solid black !important;
    color: black !important;
    background: #f9f9f9 !important;
    page-break-inside: avoid;
  }
  
  .report-prose hr { 
    border-top: 1px solid black !important;
  }
  
  @page { 
    size: A4; 
    margin: 20mm; 
    @top-center {
      content: "分析报告";
      font-size: 10pt;
      color: #666;
    }
    @bottom-center {
      content: counter(page) " / " counter(pages);
      font-size: 10pt;
      color: #666;
    }
  }
}
</style>