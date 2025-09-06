import './polyfills/end-of-stream-fix'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import App from './App.vue'
import router from './router'
import i18n from './locales'
import { initializeTheme } from './utils/theme'
import websocketPlugin from './services/websocket'
import './style.css'
import './styles/common.css'
import './styles/toast.css'




const pinia = createPinia()
const app = createApp(App)

// 初始化专业主题系统
initializeTheme()

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  // Vue Error logged
  // Component logged
  // Info logged
  
  // 如果是vnode相关的错误，静默处理
  if (err && err.message && err.message.includes('vnode')) {
    return
  }
  
  // 如果是组件销毁相关的错误，也静默处理
  if (err && err.message && (err.message.includes('Cannot set properties of null') || err.message.includes('Cannot destructure'))) {
    return
  }
}

// 处理未捕获的Promise错误
window.addEventListener('unhandledrejection', (event) => {
  // Unhandled Promise Rejection logged
  // 防止控制台显示错误
  event.preventDefault()
})

// Toast 配置
const toastOptions = {
  position: 'top-right',
  timeout: 3000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.6,
  showCloseButtonOnHover: false,
  hideProgressBar: false,
  closeButton: 'button',
  icon: true,
  rtl: false
}

// 安装插件
app.use(pinia)
app.use(router)
app.use(i18n)
app.use(websocketPlugin)
app.use(Toast, toastOptions)



// 主题系统已在上方初始化

app.mount('#app') 